"""Creates the sample_docs folder next to this file. Run:  python setup_samples.py"""
import os

FILES = {'refund_policy.md': '# Refund Policy\n\nLast updated: 2026-09-15\n\nCustomers may request a refund within 30 days of purchase. Items must be unused and in their original packaging.\n\nRefund requests must be submitted by email to support@examplestore.com. Refunds are issued to the original payment method within 7 business days after the returned item is received.\n\nDigital products are non-refundable once downloaded.\n', 'shipping_policy.md': '# Shipping Policy\n\nLast updated: 2024-01-10\n\nStandard shipping takes 5 to 7 business days. Express shipping takes 2 business days.\n\nOrders over $50 qualify for free standard shipping. International shipping is available to Canada and the United Kingdom only.\n', 'warranty_policy.md': '# Warranty Policy\n\nAll electronic products include a 1-year limited warranty covering manufacturing defects.\n\nThe warranty does not cover accidental damage, water damage, or unauthorized repairs. To make a warranty claim, contact support with your order number and a photo of the defect.\n'}

folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_docs")
os.makedirs(folder, exist_ok=True)
for name, text in FILES.items():
    with open(os.path.join(folder, name), "w", encoding="utf-8") as f:
        f.write(text)
    print("created", os.path.join(folder, name))