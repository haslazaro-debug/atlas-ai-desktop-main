import os
import logging

logger = logging.getLogger("atlas.sales_engine")

# Директория для хранения базы знаний каждого бизнеса (по ID страницы)
KNOWLEDGE_BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base")
os.makedirs(KNOWLEDGE_BASE_DIR, exist_ok=True)


def save_business_document(business_id: str, file_path: str, original_filename: str) -> str:
    """
    Сохраняет загруженный владельцем файл (Excel, CSV или текст) в папку бизнеса.
    """
    biz_dir = os.path.join(KNOWLEDGE_BASE_DIR, str(business_id))
    os.makedirs(biz_dir, exist_ok=True)

    destination_path = os.path.join(biz_dir, original_filename)

    with open(file_path, "rb") as f_src, open(destination_path, "wb") as f_dst:
        f_dst.write(f_src.read())

    logger.info(f"📁 Файл {original_filename} успешно сохранен для бизнеса ID: {business_id}")
    return destination_path


def load_business_knowledge(business_id: str) -> str:
    """
    Считывает все файлы бизнеса (Excel, CSV, TXT, MD) и конвертирует их
    в единый текстовый контекст для передачи ИИ-продажнику.
    """
    biz_dir = os.path.join(KNOWLEDGE_BASE_DIR, str(business_id))
    if not os.path.exists(biz_dir):
        return "База знаний пуста. У владельца бизнеса пока нет загруженных прайсов и описаний."

    context_parts = []

    for filename in sorted(os.listdir(biz_dir)):
        file_path = os.path.join(biz_dir, filename)
        ext = filename.rsplit(".", 1)[-1].lower()

        try:
            if ext in ["xls", "xlsx"]:
                import pandas as pd
                excel_data = pd.read_excel(file_path, sheet_name=None)
                for sheet_name, df in excel_data.items():
                    text_table = df.to_string(index=False)
                    context_parts.append(
                        f"--- Документ: {filename} (Лист: {sheet_name}) ---\n{text_table}\n"
                    )

            elif ext == "csv":
                import pandas as pd
                df = pd.read_csv(file_path)
                text_table = df.to_string(index=False)
                context_parts.append(f"--- Документ: {filename} ---\n{text_table}\n")

            elif ext in ["txt", "md"]:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                context_parts.append(f"--- Документ: {filename} ---\n{content}\n")

            else:
                logger.debug(f"Пропуск файла с неизвестным расширением: {filename}")

        except Exception as e:
            logger.error(
                f"❌ Ошибка при чтении файла {filename} для бизнеса {business_id}: {e}"
            )

    if not context_parts:
        return "База знаний пуста."

    return "\n".join(context_parts)


def list_business_documents(business_id: str) -> list[dict]:
    """
    Возвращает список загруженных документов для данного бизнеса
    вместе с их именами и размерами.
    """
    biz_dir = os.path.join(KNOWLEDGE_BASE_DIR, str(business_id))
    if not os.path.exists(biz_dir):
        return []

    docs = []
    for filename in sorted(os.listdir(biz_dir)):
        file_path = os.path.join(biz_dir, filename)
        try:
            size_kb = round(os.path.getsize(file_path) / 1024, 1)
            docs.append({"filename": filename, "size_kb": size_kb})
        except OSError:
            pass
    return docs


def delete_business_document(business_id: str, filename: str) -> bool:
    """
    Удаляет конкретный документ из базы знаний бизнеса.
    Возвращает True если файл успешно удалён.
    """
    file_path = os.path.join(KNOWLEDGE_BASE_DIR, str(business_id), filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        logger.info(f"🗑️ Файл {filename} удалён для бизнеса ID: {business_id}")
        return True
    logger.warning(f"Файл {filename} не найден для бизнеса {business_id}")
    return False
