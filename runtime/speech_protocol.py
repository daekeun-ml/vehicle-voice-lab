"""Accept complete JSON, optionally wrapped in one Markdown code fence."""
import json

def complete_json_text(raw, default_control_reply=False):
    text=raw.strip()
    if text.startswith('```') and text.endswith('```'):
        opening,separator,body=text.partition('\n')
        if separator and opening.strip() in ('```','```json'):
            text=body[:-3].strip()
    parsed=json.loads(text)
    # MiMo sometimes omits the unused reply on a fully specified control.
    # The executor produces the confirmation; do not infer or alter actions.
    if default_control_reply and isinstance(parsed,dict) and parsed.get('intent')=='control' and isinstance(parsed.get('actions'),list) and parsed['actions'] and 'reply' not in parsed:
        parsed['reply']=''
        text=json.dumps(parsed,ensure_ascii=False)
    return text
