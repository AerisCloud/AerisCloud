require 'erb'
require 'shellwords'

require File.expand_path('vagrant/aeris', File.dirname(__FILE__))
require File.expand_path('vagrant/environment', File.dirname(__FILE__))

unless Vagrant.has_plugin?("persistent_storage")
  puts "\e[31mERROR:\e[0m\tThe vagrant-persistent-storage plugin is not installed!"
  puts "\e[31mERROR:\e[0m\tPlease run: \e[36maeris update\e[0m."
  exit 1
end

unless Vagrant.has_plugin?("vagrant-triggers")
  puts "\e[31mERROR:\e[0m\tThe vagrant-triggers plugin is not installed!"
  puts "\e[31mERROR:\e[0m\tPlease run: \e[36maeris update\e[0m."
  exit 1
end

PROJECT = AerisCloud::Project.new ".aeriscloud.yml"

# Custom basebox URL
ENV['VAGRANT_SERVER_URL'] ||= PROJECT.basebox_url

# Finally we can define our vagrant box
VAGRANTFILE_API_VERSION = "2"
Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  # SSH config
  config.ssh.forward_agent = true

  # Mount the AerisCloud folder
  config.vm.synced_folder "#{AerisCloud::Environment::AERISCLOUD_PATH}", "/aeriscloud/", type: "nfs", :mount_options => AerisCloud::Environment::NFS_MOUNT_OPTIONS

  # Mount the project folder
  if !PROJECT.rsync?
    config.vm.synced_folder "#{Dir.pwd}", "/home/vagrant/#{PROJECT.name}/", type: "nfs", :mount_options => AerisCloud::Environment::NFS_MOUNT_OPTIONS
  end

  # Finally do the custom mounts
  PROJECT.mounts.each do |name, path|
    config.vm.synced_folder "#{path}", "/home/vagrant/#{name}/", type: "nfs", :mount_options => AerisCloud::Environment::NFS_MOUNT_OPTIONS
  end

  # Setup boxes
  PROJECT.boxes.each_with_index do |box, index|
    config.vm.define box.name, primary: box.primary?, autostart: box.primary? do |base|
      base.vm.box = box.basebox

      # Set IP
      base.vm.network :private_network, ip: box.ip

      # Forward ports
      box.forwards.each do |name, port|
        base.vm.network :forwarded_port, id: "#{name}", guest: port[:src], host: port[:dest]
      end

      # Setup rsync trigger
      if PROJECT.rsync?
        config.trigger.after [:up, :resume, :reload, :provision], stdout: false do
          box.rsync!
        end
      end

      # Setup virtualbox options
      base.vm.provider :virtualbox do |vb, override|
        vb.name = box.vm_name
        vb.gui = AerisCloud::Environment::GUI_ENABLED

        box.config.each do |key, value|
          vb.customize ["modifyvm", :id, "--#{key}", value]
        end

        # Force IP config
        vb.customize ["guestproperty", "set", vb.name, "/VirtualBox/GuestInfo/Net/1/V4/IP", box.ip]
        vb.customize ["guestproperty", "set", vb.name, "/VirtualBox/GuestInfo/Net/1/V4/Broadcast", box.broadcast]
        vb.customize ["guestproperty", "set", vb.name, "/VirtualBox/GuestInfo/Net/1/V4/Netmask", box.netmask]

        # Data disk configuration
        file_to_disk = box.disk_path
        override.persistent_storage.enabled = true
        override.persistent_storage.location = file_to_disk
        override.persistent_storage.size = 200 * 1024
        override.persistent_storage.use_lvm = false
        override.persistent_storage.format = false
        override.persistent_storage.mount = false
      end

      # Setup provisioning
      if box.provision?
        # Ansible provisioner
        base.vm.provision "ansible" do |ansible|
          ansible.playbook = "#{AerisCloud::Environment::ORGANIZATIONS_PATH}/#{PROJECT.organization}/env_dev.yml"

          ansible.verbose = PROJECT.debug
          ansible.raw_arguments = [
            "--extra-vars=@#{Dir.pwd}/.aeriscloud.yml",
            "--extra-vars=ansible_ssh_private_key_file=\"#{box.private_key}\""
          ]

          # SSH flags
          ansible.host_key_checking = false
          ansible.raw_ssh_args = [
            "-o Cipher=arcfour",
            "-o Compression=no",
          ]

          # Tags setup
          ansible.tags = "inventory,#{AerisCloud::Environment::ANSIBLE_TAGS}" unless AerisCloud::Environment::ANSIBLE_TAGS.nil?
          ansible.skip_tags = AerisCloud::Environment::ANSIBLE_SKIP_TAGS unless AerisCloud::Environment::ANSIBLE_SKIP_TAGS.nil?
        end
      end

      # Default shell provisioner
      base.vm.provision "shell" do |shell|
        # Render the shell file using our current context
        script = ERB.new(IO.read("#{AerisCloud::Environment::AERISCLOUD_PATH}/vagrant/shell_provisioner.rsh")).result(binding)

        shell.keep_color = true
        shell.inline = script
        shell.privileged = false
      end

      # Extra shell provisioners
      provisioners_path = File.join AerisCloud::Environment::ORGANIZATIONS_PATH, PROJECT.organization, "provisioners"
      if Dir.exists? provisioners_path
        Dir.new(provisioners_path).entries.each do |file|
          fname = File.join(provisioners_path, file)
          # Check that file exists and ends with sh (for .rsh and .sh)
          if File.file?(fname) && fname.end_with?("sh")
            base.vm.provision "shell" do |shell|
              # Render the shell file using our current context
              script = ERB.new(IO.read(fname)).result(binding)

              shell.keep_color = true
              shell.inline = script
              shell.privileged = false
            end
          end
        end
      end
    end
  end
end
