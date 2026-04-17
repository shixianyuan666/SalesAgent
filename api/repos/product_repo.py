from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from api.core.db import get_conn, json_dump, json_load
from api.core.id import new_id, now_iso
from api.models import Product, ProductCreate, ProductImage, ProductStatus, ProductUpdate


@dataclass(frozen=True)
class ProductRepo:
    def list_products(
        self,
        query: str | None,
        status: ProductStatus | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Product], int]:
        where = []
        params: list[object] = []

        if status:
            where.append("status = ?")
            params.append(status)

        if query:
            where.append(
                "(title LIKE ? OR sku LIKE ? OR description LIKE ? OR tags_json LIKE ?)"
            )
            q = f"%{query}%"
            params.extend([q, q, q, q])

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        offset = (page - 1) * page_size

        with get_conn() as conn:
            total_row = conn.execute(
                f"SELECT COUNT(1) AS cnt FROM product {where_sql}", params
            ).fetchone()
            total = int(total_row["cnt"]) if total_row else 0

            rows = conn.execute(
                f"""
                SELECT *
                FROM product
                {where_sql}
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()

        products = [self._row_to_product(r) for r in rows]
        return products, total

    def get_product(self, product_id: str) -> Product | None:
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM product WHERE id = ?", (product_id,)).fetchone()
            if not row:
                return None
            product = self._row_to_product(row)
            images = conn.execute(
                "SELECT * FROM product_image WHERE product_id = ? ORDER BY created_at ASC",
                (product_id,),
            ).fetchall()
            product.images = [self._row_to_image(r) for r in images]
            return product

    def create_product(self, data: ProductCreate) -> Product:
        product_id = new_id("prod")
        now = now_iso()
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO product (id, title, sku, description, tags_json, status, external_url, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product_id,
                    data.title,
                    data.sku,
                    data.description,
                    json_dump(data.tags),
                    data.status,
                    data.external_url,
                    now,
                    now,
                ),
            )
            row = conn.execute("SELECT * FROM product WHERE id = ?", (product_id,)).fetchone()
        return self._row_to_product(row)

    def update_product(self, product_id: str, data: ProductUpdate) -> Product | None:
        fields = []
        params: list[object] = []

        def set_field(name: str, value: object) -> None:
            fields.append(f"{name} = ?")
            params.append(value)

        if data.title is not None:
            set_field("title", data.title)
        if data.sku is not None:
            set_field("sku", data.sku)
        if data.description is not None:
            set_field("description", data.description)
        if data.tags is not None:
            set_field("tags_json", json_dump(data.tags))
        if data.status is not None:
            set_field("status", data.status)
        if data.external_url is not None:
            set_field("external_url", data.external_url)

        if not fields:
            return self.get_product(product_id)

        set_field("updated_at", now_iso())
        params.append(product_id)

        with get_conn() as conn:
            conn.execute(f"UPDATE product SET {', '.join(fields)} WHERE id = ?", params)
            row = conn.execute("SELECT * FROM product WHERE id = ?", (product_id,)).fetchone()
            if not row:
                return None
        return self._row_to_product(row)

    def set_product_embedding(self, product_id: str, embedding: list[float] | None) -> None:
        with get_conn() as conn:
            conn.execute(
                "UPDATE product SET embedding_json = ?, updated_at = ? WHERE id = ?",
                (json_dump(embedding) if embedding is not None else None, now_iso(), product_id),
            )

    def list_products_with_embeddings(self) -> list[tuple[str, list[float]]]:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT id, embedding_json FROM product WHERE embedding_json IS NOT NULL AND status = 'active'"
            ).fetchall()
        result: list[tuple[str, list[float]]] = []
        for r in rows:
            emb = json_load(r["embedding_json"], [])
            if isinstance(emb, list) and emb:
                result.append((str(r["id"]), [float(x) for x in emb]))
        return result

    def list_active_products_basic(self) -> list[Product]:
        with get_conn() as conn:
            rows = conn.execute("SELECT * FROM product WHERE status = 'active'").fetchall()
        return [self._row_to_product(r) for r in rows]

    def add_images(self, product_id: str, filenames: list[str]) -> list[ProductImage]:
        uploads_base = Path(os.environ.get("APP_UPLOADS_DIR", Path(__file__).resolve().parent.parent / "uploads"))
        now = now_iso()
        images: list[ProductImage] = []
        with get_conn() as conn:
            for fn in filenames:
                image_id = new_id("img")
                url = f"/uploads/{fn}"
                conn.execute(
                    """
                    INSERT INTO product_image (id, product_id, url, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (image_id, product_id, url, now),
                )
                images.append(
                    ProductImage(id=image_id, product_id=product_id, url=url, created_at=now)
                )
        uploads_base.mkdir(parents=True, exist_ok=True)
        return images

    def delete_image(self, product_id: str, image_id: str) -> bool:
        with get_conn() as conn:
            row = conn.execute(
                "SELECT url FROM product_image WHERE id = ? AND product_id = ?",
                (image_id, product_id),
            ).fetchone()
            if not row:
                return False
            url = str(row["url"])
            conn.execute(
                "DELETE FROM product_image WHERE id = ? AND product_id = ?",
                (image_id, product_id),
            )

        if url.startswith("/uploads/"):
            fn = url.removeprefix("/uploads/")
            uploads_base = Path(
                os.environ.get("APP_UPLOADS_DIR", Path(__file__).resolve().parent.parent / "uploads")
            )
            fp = uploads_base / fn
            try:
                fp.unlink(missing_ok=True)
            except Exception:
                pass
        return True

    def list_images(self, product_id: str) -> list[ProductImage]:
        with get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM product_image WHERE product_id = ? ORDER BY created_at ASC",
                (product_id,),
            ).fetchall()
        return [self._row_to_image(r) for r in rows]

    def _row_to_product(self, row) -> Product:
        tags = json_load(row["tags_json"], [])
        if not isinstance(tags, list):
            tags = []
        return Product(
            id=str(row["id"]),
            title=str(row["title"]),
            sku=str(row["sku"]) if row["sku"] is not None else None,
            description=str(row["description"]) if row["description"] is not None else None,
            tags=[str(x) for x in tags],
            status=str(row["status"]),
            external_url=str(row["external_url"]),
            images=[],
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def _row_to_image(self, row) -> ProductImage:
        return ProductImage(
            id=str(row["id"]),
            product_id=str(row["product_id"]),
            url=str(row["url"]),
            created_at=str(row["created_at"]),
        )

