import os
import requests
from urllib.parse import urlparse

# -------- CONFIG --------
SAVE_DIR = "papers"
os.makedirs(SAVE_DIR, exist_ok=True)

papers = [
    # 1. Foundational
    ("ULMFiT", "https://arxiv.org/abs/1801.06146"),
    ("ELMo", "https://arxiv.org/abs/1802.05365"),
    ("GPT-1", "https://openai.com/research/language-unsupervised"),

    # 2. Full FT
    ("BERT", "https://arxiv.org/abs/1810.04805"),
    ("RoBERTa", "https://arxiv.org/abs/1907.11692"),
    ("T5", "https://arxiv.org/abs/1910.10683"),

    # 3. PEFT
    ("Adapters", "https://arxiv.org/abs/1902.00751"),
    ("Prefix-Tuning", "https://arxiv.org/abs/2101.00190"),
    ("Prompt Tuning", "https://arxiv.org/abs/2104.08691"),
    ("LoRA", "https://arxiv.org/abs/2106.09685"),
    ("QLoRA", "https://arxiv.org/abs/2305.14314"),
    ("DoRA", "https://arxiv.org/abs/2402.09353"),

    # 4. Instruction FT
    ("FLAN", "https://arxiv.org/abs/2109.01652"),
    ("InstructGPT", "https://arxiv.org/abs/2203.02155"),
    ("Self-Instruct", "https://arxiv.org/abs/2212.10560"),
    ("Alpaca", "https://github.com/tatsu-lab/stanford_alpaca"),

    # 5. Alignment
    ("Deep RLHF", "https://arxiv.org/abs/1706.03741"),
    ("DPO", "https://arxiv.org/abs/2305.18290"),
    ("KTO", "https://arxiv.org/abs/2402.01306"),
    ("ORPO", "https://arxiv.org/abs/2403.07691"),

    # 6. Recent
    ("GaLore", "https://arxiv.org/abs/2403.03507"),
    ("ReFT", "https://arxiv.org/abs/2404.03592"),
    ("LISA", "https://arxiv.org/abs/2403.17919"),
    ("SimPO", "https://arxiv.org/abs/2405.14734"),
]

# -------- HELPERS --------
def get_pdf_url(url):
    if "arxiv.org/abs/" in url:
        return url.replace("/abs/", "/pdf/") + ".pdf"
    elif url.endswith(".pdf"):
        return url
    else:
        return None  # unknown format

def download_file(name, url):
    try:
        pdf_url = get_pdf_url(url)

        if pdf_url is None:
            print(f"[SKIP] {name} → No direct PDF (manual needed)")
            return

        response = requests.get(pdf_url, stream=True, timeout=15)
        if response.status_code == 200:
            filename = os.path.join(SAVE_DIR, f"{name}.pdf")
            with open(filename, "wb") as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"[OK] {name}")
        else:
            print(f"[FAIL] {name} → Status {response.status_code}")

    except Exception as e:
        print(f"[ERROR] {name} → {e}")

# -------- RUN --------
for name, url in papers:
    download_file(name, url)

print("\nDone.")