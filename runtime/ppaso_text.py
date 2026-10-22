"""Preserve decimal fractions and minus signs before Ppaso's integer-only G2P."""
import re

def normalize_ppaso_text(text):
    digits = "영일이삼사오육칠팔구"
    text = re.sub(r"(?<!\d)-(?=\d)", "마이너스 ", text)
    return re.sub(r"(\d+)\.(\d+)", lambda m: m[1]+"점"+"".join(digits[int(c)] for c in m[2]), text)
