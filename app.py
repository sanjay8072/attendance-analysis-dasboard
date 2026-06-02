from flask import Flask, render_template, jsonify, request, redirect, url_for, session
import pandas as pd
import numpy as np
import os
import shutil
import shutil
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'change-this-secret')

import json
import uuid

VALID_USERS = {
    'sanjay r': 'sanjay123'   
}


def generate_sample_data(path, days=30, students=8):
	rng = pd.date_range(end=pd.Timestamp.today().normalize(), periods=days)
	student_names = [f"Student {i+1}" for i in range(students)]
	rows = []
	for d in rng:
		for sid, name in enumerate(student_names, start=1):
			# simulate attendance with some randomness
			present = np.random.choice([1, 0], p=[0.9, 0.1])
			rows.append({"date": d.strftime('%Y-%m-%d'), "student_id": sid, "student_name": name, "present": int(present)})
	df = pd.DataFrame(rows)
	os.makedirs(os.path.dirname(path), exist_ok=True)
	df.to_csv(path, index=False)
	return df


# shareable links storage
SHARES_PATH = os.path.join(os.path.dirname(__file__), 'shares.json')

def load_shares():
	if not os.path.exists(SHARES_PATH):
		return {}
	try:
		with open(SHARES_PATH, 'r', encoding='utf-8') as f:
			return json.load(f)
	except Exception:
		return {}

def save_shares(shares):
	with open(SHARES_PATH, 'w', encoding='utf-8') as f:
		json.dump(shares, f)

def is_token_valid(token):
	shares = load_shares()
	info = shares.get(token)
	if not info:
		return False
	# check expiry
	exp = info.get('expires')
	if not exp:
		return True
	try:
		exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
		return datetime.utcnow().date() <= exp_date
	except Exception:
		return False


DATA_PATH = os.path.join(os.path.dirname(__file__), 'data', 'attendance.csv')
SAMPLE_DATA_PATH = os.path.join(os.path.dirname(__file__), 'sample_attendance.csv')
BACKUP_DIR = os.path.join(os.path.dirname(__file__), 'backups')


def ensure_backup_dir():
	os.makedirs(BACKUP_DIR, exist_ok=True)


def backup_data_file():
	if os.path.exists(DATA_PATH):
		ensure_backup_dir()
		timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
		backup_path = os.path.join(BACKUP_DIR, f'attendance_{timestamp}.csv')
		shutil.copy2(DATA_PATH, backup_path)
BACKUP_DIR = os.path.join(os.path.dirname(__file__), 'backups')


def ensure_backup_dir():
	os.makedirs(BACKUP_DIR, exist_ok=True)


def backup_data_file():
	if os.path.exists(DATA_PATH):
		ensure_backup_dir()
		timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
		backup_path = os.path.join(BACKUP_DIR, f'attendance_{timestamp}.csv')
		shutil.copy2(DATA_PATH, backup_path)


def load_data():
	if os.path.exists(DATA_PATH):
		path = DATA_PATH
	elif os.path.exists(SAMPLE_DATA_PATH):
		path = SAMPLE_DATA_PATH
	else:
		df = generate_sample_data(DATA_PATH)
		return df

	df = pd.read_csv(path, parse_dates=['date'])
	if df['date'].dtype == 'datetime64[ns]':
		df['date'] = df['date'].dt.strftime('%Y-%m-%d')
	return df


def save_data(df):
	# ensure date column is formatted as yyyy-mm-dd strings
	if 'date' in df.columns:
		df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
	os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
	backup_data_file()
	df.to_csv(DATA_PATH, index=False)


def apply_date_filters(df):
	start = request.args.get('start_date')
	end = request.args.get('end_date')
	if start:
		try:
			start_date = pd.to_datetime(start)
			df = df[pd.to_datetime(df['date']) >= start_date]
		except Exception:
			pass
	if end:
		try:
			end_date = pd.to_datetime(end)
			df = df[pd.to_datetime(df['date']) <= end_date]
		except Exception:
			pass
	return df


def login_required(view):
	@wraps(view)
	def wrapped_view(*args, **kwargs):
		if not session.get('user'):
			return redirect(url_for('login'))
		return view(*args, **kwargs)
	return wrapped_view


@app.route('/')
@login_required
def index():
	return render_template('index.html', user=session.get('user'))


@app.route('/login', methods=['GET', 'POST'])
def login():
	message = ''
	if request.method == 'POST':
		username = request.form.get('username', '').strip()
		password = request.form.get('password', '').strip()
		if VALID_USERS.get(username) == password:
			session['user'] = username
			return redirect(url_for('index'))
		message = 'Invalid username or password'
	return render_template('login.html', message=message)


@app.route('/logout')
def logout():
	session.clear()
	return redirect(url_for('login'))


@app.route('/api/daily_rates')
@login_required
def daily_rates():
	df = load_data()
	df = apply_date_filters(df)
	df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
	daily = df.groupby('date')['present'].mean().reset_index()
	daily['present_rate'] = (daily['present'] * 100).round(2)
	return jsonify(daily[['date', 'present_rate']].to_dict(orient='records'))


@app.route('/api/absences')
@login_required
def absences():
	df = load_data()
	df = apply_date_filters(df)
	# return absences by student including student_id for drilldown
	misses = df[df['present'] == 0].groupby(['student_id', 'student_name']).size().reset_index(name='absences')
	misses = misses.sort_values('absences', ascending=False)
	# ensure student_id is int
	misses['student_id'] = misses['student_id'].astype(int)
	return jsonify(misses.to_dict(orient='records'))


@app.route('/api/upload', methods=['POST'])
@login_required
def upload():
	if 'attendance' not in request.files:
		return jsonify({'status': 'error', 'message': 'No attendance file provided'}), 400
	file = request.files['attendance']
	try:
		df = pd.read_csv(file)
	except Exception as exc:
		return jsonify({'status': 'error', 'message': f'Failed to parse CSV: {exc}'}), 400

	required = {'date', 'student_id', 'student_name', 'present'}
	if not required.issubset(set(df.columns)):
		return jsonify({'status': 'error', 'message': 'CSV must contain date, student_id, student_name, present columns'}), 400

	# normalize present values
	if df['present'].dtype == 'bool':
		df['present'] = df['present'].astype(int)
	elif df['present'].dtype == object:
		mapping = {'yes': 1, 'y': 1, 'true': 1, '1': 1, 'present': 1, 'no': 0, 'n': 0, 'false': 0, '0': 0, 'absent': 0}
		df['present'] = df['present'].astype(str).str.strip().str.lower().map(mapping).fillna(df['present'])
	try:
		df['present'] = df['present'].astype(int)
	except Exception:
		return jsonify({'status': 'error', 'message': 'present column must contain 0/1 or yes/no values'}), 400

	# preserve student ids as ints
	try:
		df['student_id'] = df['student_id'].astype(int)
	except Exception:
		return jsonify({'status': 'error', 'message': 'student_id must be integers'}), 400

	# normalize dates
	try:
		df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
	except Exception:
		return jsonify({'status': 'error', 'message': 'date column must be parseable as dates'}), 400

	save_data(df)
	return jsonify({'status': 'ok', 'rows': len(df)})


@app.route('/api/students')
@login_required
def students():
	df = load_data()
	students = df[['student_id', 'student_name']].drop_duplicates().sort_values('student_id')
	# convert types for JSON
	students['student_id'] = students['student_id'].astype(int)
	return jsonify(students.to_dict(orient='records'))


@app.route('/api/student/<int:student_id>')
@login_required
def student_data(student_id):
	df = load_data()
	df = df[df['student_id'].astype(int) == int(student_id)].sort_values('date')
	out = df[['date', 'present']].to_dict(orient='records')
	return jsonify(out)


@app.route('/student/<int:student_id>')
@login_required
def student_page(student_id):
	df = load_data()
	row = df[df['student_id'].astype(int) == int(student_id)][['student_name']]
	name = row['student_name'].iloc[0] if not row.empty else f'Student {student_id}'
	return render_template('student.html', student_id=student_id, student_name=name)


@app.route('/api/update_names', methods=['POST'])
@login_required
def update_names():
	payload = request.get_json() or []
	# payload: list of {student_id, student_name}
	mapping = {int(item['student_id']): item['student_name'] for item in payload}
	df = load_data()
	df['student_id'] = df['student_id'].astype(int)
	df['student_name'] = df['student_id'].map(mapping).fillna(df['student_name'])
	save_data(df)
	return jsonify({'status': 'ok', 'updated': len(mapping)})


@app.route('/api/summary')
@login_required
def summary():
	df = load_data()
	df = apply_date_filters(df)
	total_days = df['date'].nunique()
	total_students = df['student_id'].nunique()
	attendance_rate = round(df['present'].mean() * 100, 1) if len(df) else 0
	total_absences = int((df['present'] == 0).sum())
	return jsonify({
		'total_days': total_days,
		'total_students': total_students,
		'average_attendance': attendance_rate,
		'total_absences': total_absences
	})


@app.route('/api/share/generate', methods=['POST'])
@login_required
def generate_share():
	payload = request.get_json() or {}
	days = int(payload.get('days', 7))
	note = payload.get('note', '')
	token = uuid.uuid4().hex[:8]
	created = datetime.utcnow().strftime('%Y-%m-%d')
	expires = (datetime.utcnow().date() + timedelta(days=days)).strftime('%Y-%m-%d')
	shares = load_shares()
	shares[token] = {'created': created, 'expires': expires, 'note': note}
	save_shares(shares)
	full_url = url_for('share_view', token=token, _external=True)
	return jsonify({'status': 'ok', 'url': full_url, 'token': token, 'expires': expires})


@app.route('/share/<token>')
def share_view(token):
	if not is_token_valid(token):
		return "Not found or expired", 404
	return render_template('public_index.html', token=token)


@app.route('/share_api/daily_rates/<token>')
def share_daily(token):
	if not is_token_valid(token):
		return jsonify({'error': 'invalid token'}), 404
	df = load_data()
	df = apply_date_filters(df)
	df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
	daily = df.groupby('date')['present'].mean().reset_index()
	daily['present_rate'] = (daily['present'] * 100).round(2)
	return jsonify(daily[['date', 'present_rate']].to_dict(orient='records'))


@app.route('/share_api/absences/<token>')
def share_absences(token):
	if not is_token_valid(token):
		return jsonify({'error': 'invalid token'}), 404
	df = load_data()
	df = apply_date_filters(df)
	misses = df[df['present'] == 0].groupby(['student_id', 'student_name']).size().reset_index(name='absences')
	misses = misses.sort_values('absences', ascending=False)
	misses['student_id'] = misses['student_id'].astype(int)
	return jsonify(misses.to_dict(orient='records'))


@app.route('/share_api/summary/<token>')
def share_summary(token):
	if not is_token_valid(token):
		return jsonify({'error': 'invalid token'}), 404
	df = load_data()
	df = apply_date_filters(df)
	total_days = df['date'].nunique()
	total_students = df['student_id'].nunique()
	attendance_rate = round(df['present'].mean() * 100, 1) if len(df) else 0
	total_absences = int((df['present'] == 0).sum())
	return jsonify({
		'total_days': total_days,
		'total_students': total_students,
		'average_attendance': attendance_rate,
		'total_absences': total_absences
	})


if __name__ == '__main__':
	debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() in ('1', 'true', 'yes')
	app.run(debug=debug_mode)

