from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # این خط اجازه دسترسی از همه مبدأها رو می‌ده

# تابع شبیه‌سازی برای اجرای playbook‌ها
def run_playbook(playbook_name, extra_vars=None):
    # چون Ansible نداری، فقط یه پاسخ شبیه‌سازی‌شده برمی‌گردونیم
    return {"status": "success", "message": f"Playbook {playbook_name} executed successfully"}

# endpoint برای گرفتن وضعیت دستگاه‌ها (VyOS)
@app.route('/devices', methods=['GET'])
def get_devices_status():
    result = run_playbook('ansible/playbooks/vyos_config.yml')
    if result["status"] == "success":
        return jsonify({"status": "دستگاه‌های شبکه (VyOS): پیکربندی شده"})
    return jsonify(result)

# endpoint برای گرفتن وضعیت سرورها
@app.route('/servers', methods=['GET'])
def get_servers_status():
    result = run_playbook('ansible/playbooks/server_config.yml')
    if result["status"] == "success":
        return jsonify({"status": "سرورها: پیکربندی پایه اعمال شده"})
    return jsonify(result)

# endpoint برای گرفتن وضعیت مانیتورینگ
@app.route('/monitoring', methods=['GET'])
def get_monitoring_status():
    result = run_playbook('ansible/playbooks/monitoring_config.yml')
    if result["status"] == "success":
        return jsonify({"status": "مانیتورینگ: Prometheus و Grafana فعال"})
    return jsonify(result)

# endpoint برای اعمال تنظیمات
@app.route('/configure', methods=['POST'])
def configure_device():
    data = request.get_json()
    device = data.get('device')
    command = data.get('command')
    playbook_name = 'ansible/playbooks/vyos_config.yml' if device.startswith('device') else 'ansible/playbooks/server_config.yml'
    result = run_playbook(playbook_name, extra_vars={"command": command})
    if result["status"] == "success":
        return jsonify({"message": f"تنظیمات برای {device} اعمال شد"})
    return jsonify(result)

# endpoint برای تنظیم آستانه (مانیتورینگ)
@app.route('/set-threshold', methods=['POST'])
def set_threshold():
    data = request.get_json()
    threshold = data.get('threshold')
    result = run_playbook('ansible/playbooks/monitoring_config.yml', extra_vars={"threshold": threshold})
    if result["status"] == "success":
        return jsonify({"message": f"آستانه CPU به {threshold}% تنظیم شد"})
    return jsonify(result)

# endpoint برای اجرای اسکریپت بازیابی (بکاپ)
@app.route('/run-recovery', methods=['POST'])
def run_recovery():
    result = run_playbook('ansible/playbooks/backup_config.yml')
    if result["status"] == "success":
        return jsonify({"message": "بکاپ از سرورها و دستگاه‌ها گرفته شد"})
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)