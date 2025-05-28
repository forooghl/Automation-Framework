from flask import Flask, jsonify, request
from flask_cors import CORS
import subprocess, os
from dotenv import load_dotenv

app = Flask(__name__)
CORS(app)
api_key = os.getenv('GRAFANA_API_KEY')

def run_playbook(playbook_name, extra_vars=None):
    try:
        full_playbook_path = os.path.join('/home/vagrant/ansible/playbooks/', playbook_name)
        cmd = ['ansible-playbook', '-i', '/home/vagrant/ansible/inventories/dev/hosts.ini',  full_playbook_path]
        if extra_vars:
            extra_vars_str = " ".join([f"{k}={v}" for k, v in extra_vars.items()])
            cmd.append('--extra-vars')
            cmd.append(extra_vars_str
                    )

        # Prompt for vault password or use a file if available
        vault_password_file = '/home/vagrant/ansible/vault_password'  # Adjust path as needed
        if os.path.exists(vault_password_file):
            cmd.append('--vault-password-file=' + vault_password_file)
        else:
            return {"status": "خطایی رخ داده است", "output": "", "error": "vault password file not exist."}

        result = subprocess.run(cmd, capture_output=True, text=True)
        result.check_returncode()  # Check if the command succeeded
        return {"status": "success", "output": result.stdout, "error": ""}

    except subprocess.CalledProcessError as e:
        return {"status": "خطایی رخ داده است", "output": "", "error": f"Playbook failed: {e.stderr}"}
    except Exception as e:
        return {"status": "خطایی رخ داده است", "output": "", "error": str(e)}

def run_ansible_ping(group_name):
    try:
        cmd = [
        'ansible',
        '-i', '/home/vagrant/ansible/inventories/dev/hosts.ini',
        group_name,
        '-m', 'ping',
        '-e', '@/home/vagrant/ansible/inventories/dev/group_vars/secrets.yml'
        ]
        vault_password_file = '/home/vagrant/ansible/vault_password'
        if os.path.exists(vault_password_file):
            cmd.append('--vault-password-file=' + vault_password_file)
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        result.check_returncode()
        return {"status": "success", "output": result.stdout, "error": ""}
    except subprocess.CalledProcessError as e:
        return {"status": "غیر فعال", "output": "", "error": f"Ping failed: {e.stderr}"}
    except Exception as e:
        return {"status": "غیر فعال", "output": "", "error": str(e)}

# Endpoint to ping devices with dynamic group name
@app.route('/status', methods=['GET'])
def ping_devices():
    group_name = request.args.get('group')  # Get group name from URL query parameter
    if not group_name:
        return jsonify({"status": "error", "message": "Group name is required"}), 400
    result = run_ansible_ping(group_name)
    if result["status"] == "success":
        return jsonify({"status": "فعال", "details": result["output"]})
    return jsonify(result)

# endpoint running network device configuration playbook
@app.route('/devices', methods=['GET'])
def get_devices_status():
    result = run_playbook('vyos_config.yml')
    if result["status"] == "success":
        return jsonify({"status": "دستگاه‌های شبکه (VyOS): پیکربندی شده"})
    return jsonify(result)

# endpoint running server configuration playbook
@app.route('/servers', methods=['GET'])
def get_servers_status():
    result = run_playbook('server_config.yml')
    if result["status"] == "success":
        return jsonify({"status": "سرورها: پیکربندی پایه اعمال شده"})
    return jsonify(result)

# endpoint running monitoring playbook
@app.route('/monitoring', methods=['GET'])
def get_monitoring_status():
    result = run_playbook('monitoring_config.yml')
    if result["status"] == "success":
        return jsonify({"status": "مانیتورینگ: Prometheus و Grafana فعال"})
    return jsonify(result)

# endpoint Running backup playbook
@app.route('/run-recovery', methods=['GET'])
def run_recovery():
    result = run_playbook('backup_config.yml')
    if result["status"] == "success":
        return jsonify({"message": "بکاپ از سرورها و دستگاه‌ها گرفته شد"})
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5005)
