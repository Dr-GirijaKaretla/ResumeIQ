import os
import re
import json
import io
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
import anthropic

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB

ALLOWED_EXTENSIONS = {'pdf', 'txt', 'doc', 'docx'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_text_from_file(file):
    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    file_bytes = file.read()

    if ext == 'pdf':
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
            return text.strip()
        except Exception as e:
            return f"[PDF extraction error: {e}]"

    if ext in ('doc', 'docx'):
        try:
            import docx2txt
            return docx2txt.process(io.BytesIO(file_bytes)).strip()
        except Exception as e:
            return f"[DOCX extraction error: {e}]"

    return file_bytes.decode('utf-8', errors='ignore')


def extract_json(raw: str) -> dict:
    """Multi-strategy JSON extractor — mirrors the JS extractJSON() in the React app."""
    text = re.sub(r'```(?:json)?', '', raw, flags=re.IGNORECASE).strip()

    # Strategy 1: direct parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # Strategy 2: first { … last }
    first, last = text.find('{'), text.rfind('}')
    if first != -1 and last > first:
        try:
            return json.loads(text[first:last + 1])
        except Exception:
            pass

    # Strategy 3: brace-walking
    depth, start = 0, -1
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start != -1:
                try:
                    return json.loads(text[start:i + 1])
                except Exception:
                    start = -1

    raise ValueError("Could not parse JSON from model response.")


def call_claude(messages: list, system: str = None, max_tokens: int = 4000) -> str:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    kwargs = dict(model="claude-sonnet-4-20250514", max_tokens=max_tokens, messages=messages)
    if system:
        kwargs['system'] = system
    response = client.messages.create(**kwargs)
    return "".join(b.text for b in response.content if hasattr(b, 'text'))


# ── ROUTES ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/analyze', methods=['POST'])
def analyze():
    resume_text = _get_text('resume_file', 'resume_text')
    job_text    = _get_text('job_file',    'job_text')

    if not resume_text:
        return jsonify({'error': 'Please provide a resume.'}), 400
    if not job_text:
        return jsonify({'error': 'Please provide a job description.'}), 400
    if len(resume_text) < 50:
        return jsonify({'error': 'Resume text too short.'}), 400
    if len(job_text) < 50:
        return jsonify({'error': 'Job description too short.'}), 400

    prompt = f"""You are an expert data scientist and senior technical recruiter.

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_text}

CRITICAL: Respond ONLY with a single valid JSON object. No markdown, no backticks. Keep string values under 120 chars. Limit arrays to max 6 items.

{{"overall_score":0,"grade":"A","summary":"brief summary","sections":{{"skills_match":{{"score":0,"matched":["skill"],"missing":["skill"],"bonus":["skill"]}},"experience_match":{{"score":0,"years_required":"X yrs","years_candidate":"Y yrs","relevance_notes":"note"}},"education_match":{{"score":0,"required":"degree","candidate":"degree","notes":"note"}},"keywords_match":{{"score":0,"found":["kw"],"missing":["kw"]}},"culture_fit":{{"score":0,"signals":["signal"],"notes":"note"}}}},"strengths":["s"],"gaps":["g"],"recommendations":["r"],"ats_score":0,"interview_likelihood":"High"}}

Fill with real values. interview_likelihood must be one of: Very Low, Low, Moderate, High, Very High."""

    try:
        raw = call_claude(
            messages=[{"role": "user", "content": prompt}],
            system="You are a resume analysis API. Output only valid JSON, no surrounding text, no markdown."
        )
        result = extract_json(raw)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/suggest', methods=['POST'])
def suggest():
    resume_text = _get_text('resume_file', 'resume_text')
    job_text    = _get_text('job_file',    'job_text')

    if not resume_text or not job_text:
        return jsonify({'error': 'Resume and job description are required.'}), 400

    prompt = f"""You are an elite resume coach.

RESUME:
{resume_text}

JOB DESCRIPTION:
{job_text}

Analyze the candidate's projects and provide specific rewrites aligned to the target role.

Rules:
- "projects": one entry per project found (max 5). If no explicit projects section, infer from work experience bullets.
- All string values under 200 characters.
- Arrays max 3 items each.
- "current_bullet": short phrase from the resume describing this project.
- "improved_bullet": rewrite with a strong action verb, a metric, and 1-2 keywords from the job description.

Return ONLY this JSON (no markdown, no explanation):
{{
  "projects": [
    {{
      "name": "Project Name",
      "current_bullet": "phrase from resume",
      "issues": ["issue1", "issue2"],
      "improved_bullet": "Led rewrite of X achieving Y% improvement using Z",
      "keywords_added": ["keyword1", "keyword2"],
      "impact": "Why this rewrite is stronger"
    }}
  ],
  "general_tips": [
    {{"tip": "Tip title", "detail": "One concrete sentence."}}
  ],
  "missing_projects": ["project type that would help"],
  "overall_advice": "Two sentences on the biggest resume improvement opportunity."
}}"""

    try:
        raw = call_claude(
            messages=[{"role": "user", "content": prompt}],
            system="You are a resume coach API. Output only valid JSON objects with no surrounding text, no markdown, and no explanation."
        )
        result = extract_json(raw)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _get_text(file_key: str, text_key: str) -> str:
    f = request.files.get(file_key)
    if f and f.filename and allowed_file(f.filename):
        return extract_text_from_file(f)
    return request.form.get(text_key, '').strip()


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
