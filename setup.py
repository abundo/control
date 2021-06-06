#!/usr/bin/env python3

#
# Do basic installation/upgrade/checks
#

import os
import sys
import json
import shutil
import random
import argparse
import subprocess
import yaml

HOME = "/opt/abcontrol"
CONFIG_FILE = "/etc/abcontrol/abcontrol.yaml"
ENV_FILE = "/etc/abcontrol/abcontrol.env"


def print_header(msg):
    print()
    print(f"+----------------------------------------------------------------------------+")
    print(f"! {msg.ljust(74)} !")
    print(f"+----------------------------------------------------------------------------+")


def print_subheader(msg):
    print()
    print(f"----- {msg} ----")


class CLI:
    """
    Start a shell
    """
    def __init__(self):
        self.p = subprocess.Popen(
            "/bin/bash", 
            shell=True, 
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, 
            universal_newlines=True,
            bufsize=1)
        self.marker = "ölkasdfjlkj1345ö23ljkölsxzckvjölkjalsdf---.,asd-.asd,gv-.a,sdfkj"

    def run(self, cmd):
        self.p.stdin.write(f"{cmd}\n")
        self.p.stdin.write(f"echo {self.marker}\n")
        while True:
            line = self.p.stdout.readline().rstrip()
            if line == self.marker:
                return
            print(line)

    def close(self):
        self.p.terminate()


class Setup():

    def __init__(self, args=None):
        self.cli = CLI()
        self.args = args
        self.env = None
        self.jinja = None
        self.roles = {}   # Shortcut into config file
        self.restart_apache2 = False

    # ----------------------------------------------------------------------------+
    def create_dir(self, dir):
        if not os.path.exists(dir):
            print(f"Creating directory {dir}")
            os.makedirs(dir)

    def copy_file(self, src=None, dst=None):
        """
        Copy a file, using Jinja2 template, expanding env variables
        """
        if self.args.force or not os.path.exists(dst):
            print(f"Copying {src} template to {dst}")
            tmp = self.jinja.get_template(src).render(self.env)
            with open(dst, "w") as f:
                f.write(tmp)

    def copy_file_raw(self, src=None, dst=None):
        if self.args.force or not os.path.exists(dst):
            print(f"Copying {src} to {dst}")
            shutil.copy(src, dst)

    def setup_apache2(self, vhosts=None):
        print_header("Setup Apache2")

        self.cli.run("apt install apache2 -y")
        self.cli.run("a2enmod headers proxy proxy_http ssl")
        self.cli.run("a2dissite 000-default.conf")

        for vhost in vhosts:
            import pprint;pprint.pprint(vhost)
            self.copy_file(src=vhost["src"], dst=vhost["dst"])
            self.cli.run(f"a2ensite {vhost['name']}")
            self.restart_apache2 = True

    # ----------------------------------------------------------------------------+
    def setup_dependencies(self):
        print_header("Install dependencies, system wide")

        cmd = "apt install"
        # dependencies to build python-ldap
        cmd += " libsasl2-dev libldap2-dev libssl-dev "

        # python package handler, access control
        cmd += " python3-pip python3-venv acl"

        # docker
        cmd += " docker docker-compose"
        self.cli.run(cmd)
        self.cli.run("pip3 install orderedattrdict")    # needed by dnsmgr

    # ----------------------------------------------------------------------------+
    def setup_venv(self):
        print_subheader("Setup/activate abcontrol python virtual environment")
        if not os.path.exists(f"{HOME}/bin"):
            print_subheader("Creating python venv")
            self.cli.run(f"cd {HOME}/..")
            self.cli.run("python3 -m venv abtools")

        print_subheader("Activating python venv")
        self.cli.run(f"cd {HOME}")
        self.cli.run("source bin/activate")

        print_subheader("Install abcontrol dependencies")
        self.cli.run(f"cd {HOME}")
        self.cli.run(f"pip3 install -q -r requirements.txt -r docs/requirements.txt")
        print("done")


    # ----------------------------------------------------------------------------+
    def setup_config(self):
        if self.args.force or not os.path.exists(ENV_FILE):
            print_header(f"No {ENV_FILE} file exist")
            self.create_dir("/etc/abcontrol")
            self.copy_file_raw(src=f"{HOME}/contrib/abcontrol/abcontrol.env",
                          dst=ENV_FILE)
            print_header("Please edit the env file, then rerun this script")
            if not self.args.force:
                sys.exit(1)
        
        import dotenv
        self.env = dotenv.dotenv_values("/etc/abcontrol/abcontrol.env")
        if "DJANGO_SECRET_KEY" not in self.env:
            tmp = ""
            for i in range(50):
                tmp += random.choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)")
            self.env["DJANGO_SECRET_KEY"] = tmp
        import pprint; pprint.pprint(self.env)

        import jinja2
        self.jinja = jinja2.Environment(loader=jinja2.FileSystemLoader("/"), trim_blocks=True)

        if self.args.force or not os.path.exists(CONFIG_FILE):
            print_header(f"No {CONFIG_FILE} file exist")
            self.create_dir("/etc/abcontrol")
            self.copy_file(src=f"{HOME}/contrib/abcontrol/abcontrol.yaml",
                           dst=CONFIG_FILE)
            print_header("Please check/edit the configuration file, then rerun this script")


    # ----------------------------------------------------------------------------+
    def setup_ablib(self):
        print_header("Setup ablib")
        dst = "/opt/ablib"
        if not os.path.exists(dst):
            print_subheader(f"Installing {dst}")
            self.cli.run(f"cd /opt")
            self.cli.run(f"git clone https://github.com/abundo/ablib.git")
        print("done")


    # ----------------------------------------------------------------------------+
    def setup_abcontrol(self):
        """
        Install common functionality, needed on all servers
        """
        
        # ----------------------------------------------------------------------------+
        print_header("Setup abcontrol")

        print_subheader("Create abcontrol log directory, set permissions")
        self.create_dir("/var/log/abcontrol")
        self.cli.run(f"setfacl -R -m u:www-data:rwX /var/log/abcontrol")
        self.cli.run(f"setfacl -d -R -m u:www-data:rwX /var/log/abcontrol")
        print("done")


        print_subheader("Create abcontrol work directory, set permissions")
        self.create_dir("/var/lib/abcontrol")
        self.cli.run(f"setfacl -R -m u:www-data:rwX /var/lib/abcontrol")
        self.cli.run(f"setfacl -d -R -m u:www-data:rwX /var/lib/abcontrol")
        print("done")


        print_subheader("Create symlink to abcontrol cli")
        dst = "/usr/bin/abcontrol"
        if not os.path.exists(dst):
            self.cli.run(f"ln -s /opt/abcontrol/app/tools/abcontrol/abcontrol.sh {dst}")
        print("done")


        print_subheader("Copy config files")
        if self.roles.get("abcontrol", False):
            # Index file, for web page
            self.copy_file(src="{HOME}/contrib/abcontrol/index.yaml",
                           dst="/etc/abcontrol/index.yaml")
        
        vhosts = [
            {
                "src": f"{HOME}/contrib/abcontrol/abcontrol.conf",
                "dst": "/etc/apache2/sites-available/abcontrol.conf",
                "name": "abcontrol"
            },
        ]
        self.setup_apache2(vhosts=vhosts)

        print("done")


    # ----------------------------------------------------------------------------+

    # ----------------------------------------------------------------------------+
    def setup_becs(self):
        print_header("Setup BECS role")
        if not self.roles.get("becs", False):
            print_header("role is not enabled")
            return


    # ----------------------------------------------------------------------------+
    def setup_dns(self):

        if not self.roles.get("dns", False):
            print_header("DNS role not enabled")
            return

        # ----------------------------------------------------------------------------+
        print_header("Setup DNS role")

        print_subheader("Check if named/bind is installed")
        if not os.path.exists("/etc/bind"):
            self.cli.run(f"apt install named")
        print("done")

        # ----------------------------------------------------------------------------+
        print_subheader("Check if dnsmgr is installed")

        if not os.path.exists("/opt/dnsmgr"):
            print_subheader("Installing dnsmgr")
            self.cli.run(f"cd /opt")
            self.cli.run(f"git clone https://github.com/abundo/dnsmgr.git")

        self.create_dir("/etc/dnsmgr")
        self.copy_file(src="/opt/dnsmgr/dnsmgr-example.conf",
                       dst="/etc/dnsmgr/dnsmgr.yaml")
        self.cli.run(f"touch /etc/dnsmgr/records")
        print("done")


    # ----------------------------------------------------------------------------+
    def setup_emmgr(self):
        # print_header("check if emmgr is installed")
        # print("todo")
        pass

    # ----------------------------------------------------------------------------+
    def setup_icinga(self):
        print_header("Setup icinga role (docker)")
        if not self.roles.get("icinga", False):
            print_header("role is not enabled")
            return

        dst = "/opt/icinga"
        self.create_dir(dst)
        self.copy_file(src="contrib/icinga/docker-compose.yaml",
                       dst=dst)

        return

        vhosts = [
            {
                "src": f"{HOME}/contrib/icinga/icinga.conf",
                "dst": "/etc/apache2/sites-available/icinga.conf",
                "name": "icinga",
            },
        ]
        self.setup_apache2(vhosts=vhosts)


    # ----------------------------------------------------------------------------+
    def setup_librenms(self):
        print_header("Setup librenms role (docker)")
        if not self.roles.get("librenms", False):
            print_header("role is not enabled")
            return

        dst = "/opt/librenms"
        self.create_dir(dst)
        self.copy_file(src="contrib/librenms/docker-compose.yaml",
                       dst=dst)
        self.copy_file(src="contrib/librenms/.env",
                       dst=dst)
        self.copy_file(src="contrib/librenms/librenms.env",
                       dst=dst)
        self.copy_file(src="contrib/librenms/msmtpd.env",
                      dst=dst)
        print("done")

        vhosts = [
            {
                "src": f"{HOME}/contrib/librenms/librenms.conf",
                "dst": "/etc/apache2/sites-available/librenms.conf",
                "name": "librenms",
            },
        ]
        self.setup_apache2(vhosts=vhosts)


    # ----------------------------------------------------------------------------+
    def setup_openldap(self):
        print_header("Setup openldap & fusiondirectory role (docker)")
        if not self.roles.get("ldap", False):
            print_header("role is not enabled")
            return

        self.create_dir("/opt/openldap")
        self.copy_file(src="contrib/openldap/docker-compose.yaml", 
                       dst="/opt/openldap/docker-compose.yaml")
        print("done")

        # Apache for fusiondirectory
        vhosts = [
            {
                "src": f"{HOME}/contrib/openldap/fusiondirectory.conf",
                "dst": "/etc/apache2/sites-available/fusiondirectory.conf",
                "name": "fusiondirectory",
            },
        ]
        self.setup_apache2(vhosts=vhosts)


    # ----------------------------------------------------------------------------+
    def setup_oxidized(self):
        print_header("Setup Oxidized role (docker)")
        if not self.roles.get("oxidized", False):
            print_header("role is not enabled")
            return

        dst = "/opt/oxidized"
        self.create_dir(dst)
        self.copy_file(src="contrib/oxidized/docker-compose.yaml",
                       dst=dst)

        vhosts = [
            {
                "src": f"{HOME}/contrib/oxidized/oxidized.conf",
                "dst": "/etc/apache2/sites-available/oxidized.conf",
                "name": "oxidized",
            },
        ]
        self.setup_apache2(vhosts=vhosts)
        print("done")

    # ----------------------------------------------------------------------------+
    def setup_postgresql(self):
        print_header("Setup postgresql")
        if not self.roles.get("abcontrol", False):
            print_header("Only for abcontrol role")
            return

        dst = "/opt/postgresql"
        self.create_dir(dst)
        self.copy_file(src="contrib/oxidized/docker-compose.yaml", dst=dst)

    # ----------------------------------------------------------------------------+
    def setup_rabbitmq(self):
        print_header("Setup rabbitmq role (docker)")
        if not self.roles.get("rabbitmq", False):
            print_header("role is not enabled")
            return

        if args.force or not os.path.exists("/opt/rabbitmq"):
            self.create_dir("/opt/rabbitmq")
            if "RABBITMQ_ERLANG_COOKIE" not in self.env:
                tmp = ""
                for i in range(50):
                    tmp += random.choice("abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)")
                self.env["RABBITMQ_ERLANG_COOKIE"] = tmp

            self.copy_file(src=f"{HOME}/contrib/rabbitmq/docker-compose.yaml",
                           dst=f"/opt/rabbitmq/docker-compose.yaml")
            print("done")

            # Start 
            self.cli.run(f"cd /opt/rabbitmq")
            self.cli.run(f"docker-compose up -d")

            # Create user and set permission
            self.cli.run("cd /opt/rabbitmq")
            self.cli.run("docker-compose exec rabbitmq bash")
            #self.cli.run("rabbitmqctl add_user abcontrol <passwd>")
            #self.cli.run("rabbitmqctl change_password <user> <passwd>")
            #self.cli.run('rabbitmqctl set_permissions -p / abcontrol ".*" ".*" ".*"')
            self.cli.run("exit")



def main():
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument("--force", default=False, action="store_true")
    args = parser.parse_args()

    setup = Setup(args=args)

    # setup.setup_dependencies()

    setup.setup_venv()

    # We are now in venv and can import venv modules

    setup.setup_config()

    setup.setup_ablib()

    setup.setup_abcontrol()

    setup.setup_becs()

    setup.setup_dns()

    setup.setup_icinga()

    setup.setup_librenms()

    setup.setup_oxidized()

    setup.setup_postgresql()

    setup.setup_rabbitmq()


    # ----- now all software is is installed -----

    # ----------------------------------------------------------------------------+
    print_header("Check if postgresql database is active")
    # cli.run(f"cd /opt/postgresql")
    # cli.run(f"docker-compose up -d")
    print("NOT done")


    # ----------------------------------------------------------------------------+
    print_header("Perform Django migrations")
    setup.cli.run(f"cd {HOME}/app")
    setup.cli.run(f"./manage.py migrate")
    print("done")

    # ----------------------------------------------------------------------------+
    print_header("Check if rabbitmq is active")
    setup.cli.run(f"cd {HOME}")
    print("todo")
    print("NOT done")

    # ----------------------------------------------------------------------------+
    print_header("Check if Netbox API can be accessed")
    setup.cli.run(f"cd {HOME}")
    print("todo")
    print("NOT done")

    # ----------------------------------------------------------------------------+
    print_header("Build documentation, must be done before django collectstatic")
    setup.cli.run(f"cd {HOME}/docs")
    setup.cli.run(f"make html")
    print("done")
    
    # ----------------------------------------------------------------------------+
    print_header("Collect static files")
    setup.cli.run(f"cd {HOME}/app")
    setup.cli.run(f"./manage.py collectstatic --no-input")
    print("done")

    # ----------------------------------------------------------------------------+
    print_header("Verify/Install services")

    if setup.roles.get("abcontrol", False):
        setup.cli.run(f"systemctl stop abcontrol.service")
        setup.cli.run(f"cp {HOME}/contrib/abcontrol/abcontrol.service /etc/systemd/system")
        setup.cli.run(f"systemctl daemon-reload")
        setup.cli.run(f"systemctl enable abcontrol.service")
        setup.cli.run(f"systemctl start abcontrol.service")

    setup.cli.run(f"systemctl stop abcontrol_worker.service")
    setup.cli.run(f"cp {HOME}/contrib/abcontrol/abcontrol_worker.service /etc/systemd/system")

    setup.cli.run(f"systemctl daemon-reload")
    setup.cli.run(f"systemctl enable abcontrol_worker.service")
    setup.cli.run(f"systemctl start abcontrol_worker.service")


    print("done")

    # ----------------------------------------------------------------------------+
    print_header("Finished")
    setup.cli.close()


if __name__ == "__main__":
    main()
