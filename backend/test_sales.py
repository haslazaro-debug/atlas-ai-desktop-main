import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ai_brain import generate_sales_response

# 1. Создаём тестовую базу знаний (прайс аренды коттеджей)
business_id = "test_cottage_biz_01"
kb_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "knowledge_base", business_id)
os.makedirs(kb_dir, exist_ok=True)

dummy_price_path = os.path.join(kb_dir, "prices.txt")
with open(dummy_price_path, "w", encoding="utf-8") as f:
    f.write("""
Наш каталог и цены на коттеджи:
1. Коттедж "Forest VIP": 150 000 тенге в сутки. Вмещает до 20 человек. Есть баня, бассейн, мангальная зона. Залог: 50 000 тенге.
2. Коттедж "Mountain View": 100 000 тенге в сутки. Вмещает до 10 человек. Мангал, терраса с видом на горы. Залог: 30 000 тенге.
Условия бронирования: предоплата 30%, остальное при заезде. Шум после 23:00 запрещен на улице.
""")

print("[OK] Testovaya baza znany (prays) sozdana!\n")
print("=" * 60)
print("[ATLAS SALES TEST] Imitaciya dialoga s klientom")
print("=" * 60)

customer_id = "client_ivan_999"

# Сообщение 1: Клиент спрашивает цену в лоб
msg_1 = "Здравствуйте! Сколько стоит снять коттедж на выходные?"
print(f"\n[Клиент]: {msg_1}")
result_1 = generate_sales_response(business_id, customer_id, msg_1)
print(f"[ATLAS ({result_1['status']})]: {result_1['reply']}")

# Сообщение 2: Возражение по цене
msg_2 = "Блин, дороговато за 150к. А скидку сделать можете если на 2 дня возьмем?"
print(f"\n[Клиент]: {msg_2}")
result_2 = generate_sales_response(business_id, customer_id, msg_2)
print(f"[ATLAS ({result_2['status']})]: {result_2['reply']}")

# Сообщение 3: Нестандартный запрос (должен вызвать NEED_HUMAN)
msg_3 = "А можете зарезервировать без предоплаты и дать рассрочку на 3 месяца?"
print(f"\n[Клиент]: {msg_3}")
result_3 = generate_sales_response(business_id, customer_id, msg_3)
print(f"[ATLAS ({result_3['status']})]: {result_3['reply']}")
if result_3['status'] == 'escalate_to_human':
    print("[SYSTEM] -> Уведомление отправлено владельцу бизнеса!")


print("\n" + "=" * 60)
print("[DONE] Test zaversen! ATLAS ne slil tsenu srazu,")
print("       zadal utochnyayushchie voprosy i otrabotal vozrazhenie.")
