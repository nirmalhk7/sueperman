import csv
import io
from datetime import date

from app.schemas import ProductInput

MAX_UPLOAD = 10 * 1024 * 1024


class FixtureReceiptExtractor:
    provider_name = "csv"
    mode = "offline"

    def extract(self, content: bytes) -> list[ProductInput]:
        if len(content) > MAX_UPLOAD:
            raise ValueError("Upload exceeds 10MB")
        try:
            reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")), strict=True)
            if not reader.fieldnames:
                raise ValueError("CSV headers required")
            reader.fieldnames = [c.strip().lower() for c in reader.fieldnames]
            if "product_name" not in reader.fieldnames:
                raise ValueError("product_name required")
            seen, products = set(), []
            for row in reader:
                if None in row:
                    raise ValueError("Malformed CSV row")
                row = {k: (v or "").strip() for k, v in row.items()}
                signature = tuple(sorted(row.items()))
                if signature in seen:
                    continue
                seen.add(signature)
                order = row.get("order_id", "")
                products.append(
                    ProductInput(
                        product_name=row.get("product_name", ""),
                        brand=row.get("brand") or None,
                        model_number=row.get("model_number") or None,
                        upc=row.get("upc") or None,
                        date_purchased=date.fromisoformat(row["purchased_at"])
                        if row.get("purchased_at")
                        else None,
                        merchant=row.get("merchant") or None,
                        order_reference_redacted="***" + order[-4:] if order else None,
                    )
                )
            if not products:
                raise ValueError("No products found")
            if len(products) > 100:
                raise ValueError("At most 100 products per upload")
            return products
        except (UnicodeError, csv.Error) as exc:
            raise ValueError("Invalid UTF-8 CSV") from exc
