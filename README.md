# Daily Job Search Digest

**Rishabh Sharma** · [GitHub](https://github.com/Rishabhlv2805)

A short, scored list of public job postings matched to a resume you paste. It does not apply for you.

## What it does

1. Read only the text you provide (resume, projects, target titles, location).
2. Pull current postings from [Jobicy](https://jobicy.com), [Remote OK](https://remoteok.com), and [Arbeitnow](https://www.arbeitnow.com).
3. Score each role 0–100 and keep the strongest handful.
4. Explain fit and gaps, and suggest whether to tailor, read first, or skip.
5. Keep an application tracker you export and import. Nothing is submitted.

## Scoring

| Signal | Effect |
|---|---|
| Skills from your text appear in the posting | up to +42 |
| Title matches a target you named | +12 |
| Remote or your city is in the location line | +8 to +10 |
| Senior / staff / director title and no senior signal in the profile | −14 |

Roles are ranked by score. Accuracy of the match depends on how specific the pasted profile is.

## Missing inputs that improve the next digest

Salary range, visa or student constraints, cities you will not relocate to, and exact titles.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Applications always need your confirmation.

## License

MIT © 2026 Rishabh Sharma
