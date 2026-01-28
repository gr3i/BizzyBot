import os
print("DATABASE_URL =", os.getenv("DATABASE_URL"))
import json
import asyncio
from typing import Optional, Tuple, List, Dict, Any

from db.session import SessionLocal
from db.models import Verification

from services.vut_api import VutApiClient


# podminky: fakulta.zkratka == "FP" a typ_studia.zkratka v {"B","N"}
ALLOWED_FAKULTA = "FP"
ALLOWED_TYPY = {"B", "N"}

OUT_PATH = os.getenv("FP_CANDIDATES_OUT", "fp_candidates.json")


def parse_mail_and_ident(stored_value: str) -> Tuple[str, Optional[str]]:
    # ulozena hodnota: "mail||ident" nebo "mail"
    parts = (stored_value or "").split("||", 1)
    mail_value = parts[0].strip().lower() if parts else ""
    ident_value = parts[1].strip().lower() if len(parts) == 2 else None
    return mail_value, ident_value


def extract_fp_bn(details: Dict[str, Any], mail_value: str) -> Optional[Dict[str, Any]]:
    if not details:
        return None

    emails_api = [e.strip().lower() for e in (details.get("emaily") or [])]
    if mail_value and mail_value not in emails_api: 
        return None

    vztahy = details.get("vztahy") or []
    matched_types: List[str] = []

    for vztah in vztahy:
        fak = ((vztah.get("fakulta") or {}).get("zkratka") or "").strip().upper()
        typ = ((vztah.get("typ_studia") or {}).get("zkratka") or "").strip().upper()

        if fak == ALLOWED_FAKULTA and typ in ALLOWED_TYPY:
            matched_types.append(typ)

    if not matched_types:
        return None

    
    matched_types = sorted(set(matched_types))

    full_name = f"{details.get('jmeno_krestni','') or ''} {details.get('prijmeni','') or ''}".strip()

    return {
        "discord_user_id": None,  
        "ident": None,            
        "jmeno": full_name,
        "fakulta": ALLOWED_FAKULTA,
        "typy_studia": matched_types,
        "api_id": details.get("id"),
        "api_login": details.get("login"),
        "email": (emails_api[0] if emails_api else None),
    }


async def main():
   
    api_key = os.getenv("VUT_API_KEY")
    owner_id = os.getenv("OWNER_ID")

    if not api_key or not owner_id:
        raise RuntimeError("Missing env vars: VUT_API_KEY and/or OWNER_ID")

    vut = VutApiClient(api_key=api_key, owner_id=owner_id)
    await vut.start()

    try:
        with SessionLocal() as s:
            rows = (
                s.query(Verification)
                .filter(Verification.verified == True)
                .all()
            )

        print(f"[audit_fp] loaded verified rows: {len(rows)}")

        candidates: List[Dict[str, Any]] = []
        checked = 0
        skipped_no_ident = 0
        api_missing = 0

        for v in rows:
            discord_user_id = int(v.user_id)
            mail_value, ident_value = parse_mail_and_ident(v.mail)

            if not ident_value:
                skipped_no_ident += 1
                continue

            details = None
            try:
                details = await vut.get_user_details(ident_value)
            except Exception as e:
                print(f"[audit_fp] VUT API error ident={ident_value}: {e}")
                continue

            checked += 1

            if not details:
                api_missing += 1
                continue

            match = extract_fp_bn(details, mail_value)
            if match:
                match["discord_user_id"] = discord_user_id
                match["ident"] = ident_value
                candidates.append(match)

           
            await asyncio.sleep(0.15)

        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump(candidates, f, ensure_ascii=False, indent=2)

        print(
            f"[audit_fp] done | checked={checked} "
            f"skipped_no_ident={skipped_no_ident} api_missing={api_missing} "
            f"candidates={len(candidates)} out={OUT_PATH}"
        )

    finally:
        await vut.close()


if __name__ == "__main__":
    asyncio.run(main())

