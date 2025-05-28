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

# Helper function to convert JSON to a YAML-like string
def json_to_yaml_string(obj, indent=0):
    output = ''
    indent_str = '  ' * indent
    
    if isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                output += indent_str + '- ' + json_to_yaml_string(item, indent).lstrip()
            else:
                output += indent_str + '- ' + str(item) + '\n'
    elif isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, dict):
                output += indent_str + f"{key}:\n" + json_to_yaml_string(value, indent + 1)
            elif isinstance(value, list):
                output += indent_str + f"{key}:\n" + json_to_yaml_string(value, indent + 1)
            else:
                output += indent_str + f"{key}: {value}\n"
    else:
        output += indent_str + str(obj) + '\n'
    
    return output

def parse_role_files(role_path):
    role_data = {
        "tasks": [],
        "handlers": [],
        "templates": []
    }
    
    def parse_tasks(file_path, visited=None):
        if visited is None:
            visited = set()
        if file_path in visited:
            return []
        visited.add(file_path)
        
        if not os.path.exists(file_path):
            return []
        
        with open(file_path, 'r') as f:
            tasks_content = yaml.safe_load(f) or []
        
        tasks = []
        for task in tasks_content:
            if isinstance(task, dict):
                if 'include_tasks' in task:
                    included_file = task['include_tasks']
                    if not os.path.isabs(included_file):
                        included_file = os.path.join(os.path.dirname(file_path), included_file)
                    included_tasks = parse_tasks(included_file, visited)
                    tasks.extend(included_tasks)
                else:
                    tasks.append(task)
        return tasks
    
    tasks_path = os.path.join(role_path, 'tasks', 'main.yml')
    if os.path.exists(tasks_path):
        role_data["tasks"] = parse_tasks(tasks_path)
    
    handlers_path = os.path.join(role_path, 'handlers', 'main.yml')
    if os.path.exists(handlers_path):
        with open(handlers_path, 'r') as f:
            handlers_content = yaml.safe_load(f) or []
            for handler in handlers_content:
                if isinstance(handler, dict):
                    role_data["handlers"].append(handler)
    
    templates_path = os.path.join(role_path, 'templates')
    if os.path.exists(templates_path):
        role_data["templates"] = [f for f in os.listdir(templates_path) if f.endswith('.j2')]
    
    return role_data

def get_playbook_details(playbook_name):
    try:
        playbook_path = os.path.join('/home/vagrant/ansible/playbooks', playbook_name)
        if not os.path.exists(playbook_path):
            return {"status": "error", "message": f"Playbook {playbook_name} not found"}, 404
        
        with open(playbook_path, 'r') as f:
            playbook_content = yaml.safe_load(f)
        
        playbook_info = {
            "name": playbook_name,
            "plays": []
        }
        
        if isinstance(playbook_content, list):
            for play in playbook_content:
                play_info = {
                    "name": play.get("name", ""),
                    "hosts": play.get("hosts", ""),
                    "connection": play.get("connection", ""),
                    "gather_facts": play.get("gather_facts", True),
                    "vars_files": play.get("vars_files", []),
                    "tasks": [],
                    "roles": []
                }
                
                if 'tasks' in play:
                    for task in play['tasks']:
                        if isinstance(task, dict):
                            play_info["tasks"].append(task)
                
                if 'roles' in play:
                    for role in play['roles']:
                        role_path = os.path.join('/home/vagrant/ansible/roles', role)
                        if os.path.exists(role_path):
                            role_data = parse_role_files(role_path)
                            play_info["roles"].append({
                                "name": role,
                                "tasks": role_data["tasks"],
                                "handlers": role_data["handlers"],
                                "templates": role_data["templates"]
                            })
                
                playbook_info["plays"].append(play_info)
        
        # Convert the playbook_info to a YAML-like string
        playbook_string = json_to_yaml_string(playbook_info)
        return {"status": "success", "playbook": playbook_string}
    except Exception as e:
        return {"status": "error", "message": f"Error reading playbook {playbook_name}: {str(e)}"}, 500

# Endpoint to get and display playbook tasks
@app.route('/get-playbook', methods=['GET'])
def get_playbook():
    playbook_name = request.args.get('playbook_name')  # Get group name from URL query parameter
    result = get_playbook_details(f"{playbook_name}_config.yml")
    if result["status"] == "success":
        return jsonify({"title": f"نمایش وظایف پیکربندی {playbook_name}", "status": "success", "playbook": result["playbook"]})
    return jsonify(result)

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
