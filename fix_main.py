with open('backend/main.py', 'r') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if '@app.get("/analytics/sentiment-trend")' in line:
        new_lines.append('    db.commit()\n')
        new_lines.append('    return {"status": "success", "draft": {"id": draft.id, "content": draft.content, "status": draft.status}}\n\n\n')
        new_lines.append('@app.post("/drafts/{id}/approve")\n')
        new_lines.append('def approve_draft(id: int, db: Session = Depends(get_db)):\n')
        new_lines.append('    draft = db.get(Draft, id)\n')
        new_lines.append('    if not draft:\n')
        new_lines.append('        raise HTTPException(status_code=404, detail="Draft not found")\n')
        new_lines.append('    \n')
        new_lines.append('    email = db.get(Email, draft.email_id)\n')
        new_lines.append('    email.status = "Replied"\n')
        new_lines.append('    draft.status = "Approved"\n')
        new_lines.append('    \n')
        new_lines.append('    action = Action(\n')
        new_lines.append('        email_id=email.id,\n')
        new_lines.append('        action_type="Replied",\n')
        new_lines.append('        proposed_content=draft.content,\n')
        new_lines.append('        is_approved=True,\n')
        new_lines.append('    )\n')
        new_lines.append('    db.add(action)\n')
        new_lines.append('    db.commit()\n')
        new_lines.append('    return {"status": "success", "message": "Draft approved and sent"}\n\n\n')
        new_lines.append('# ---------------------------------------------------------------------------\n')
        new_lines.append('# Analytics and Intelligence\n')
        new_lines.append('# ---------------------------------------------------------------------------\n\n')
    new_lines.append(line)

with open('backend/main.py', 'w') as f:
    f.writelines(new_lines)
print('Done!')
