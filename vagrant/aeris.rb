# This file provides an abstraction around the .aeriscloud.yml allowing us to
# write a Vagrantfile that actually can be read by human beings

require 'yaml'
require 'log4r'

require File.expand_path('environment', File.dirname(__FILE__))

module AerisCloud
  DEFAULT_BOX = "chef/centos-7.0"
  DEFAULT_RAM = 1024
  DEFAULT_CPU = 1

  # This class wraps the .aeriscloud.yml file directly
  class Project
    attr_reader :name, :id, :basebox_url, :boxes

    def initialize(file)
      @conf = YAML::load_file(file)

      # Basic values
      @name = @conf["project_name"]
      @id = @conf["id"].to_i
      @basebox_url = @conf["basebox_url"]
      @logger = Log4r::Logger.new("aeriscloud::project")

      # Load boxes
      @boxes = []
      @conf["boxes"].each_with_index do |infra, index|
        @boxes.push(Box.new(self, index, infra))
      end
    end

    # Use the debug flag in .aeriscloud.yml, otherwise get it from the environment
    def debug()
      @conf["debug"].nil? ? Environment::ANSIBLE_DEBUG : @conf["debug"]
    end

    # Returns the list of NFS mounts defined in the conf
    def mounts()
      return {} if !@conf.key?("mounts")

      mounts = {}
      @conf["mounts"].each do |name, path|
        path = File.expand_path(path)
        raise NameError("project_name cannot be used as a NFS mount point") if name == @name
        raise NameError("Path #{path} does not exist or is not a directory") if !File.directory?(path)
        mounts[name] = path
      end

      return mounts
    end

    # Returns the organization defined in the conf, otherwise reads it from the env
    def organization()
      @conf.key?("organization") ? @conf["organization"] : Environment::ORGANIZATION
    end

    def rsync_ignores()
      rsync_ignores = ""
      if @conf['rsync_ignores']
        @conf['rsync_ignores'].each { |x| rsync_ignores = "#{rsync_ignores} --exclude=#{x}" }
      end
      return rsync_ignores
    end

    # Is resync enabled ?
    def rsync?()
      @conf["use_rsync"].nil? ? false : @conf["use_rsync"] == "true" || @conf["use_rsync"] == true
    end
  end

  # This class wraps the infras/boxes block from the configuration
  class Box
    attr_reader :name, :basebox

    def initialize(project, index, conf)
      @project = project
      @index = index
      @conf = conf

      @name = conf["name"].downcase.strip.gsub(/[^\w\.]+/, '-')
      @basebox = conf["basebox"]
      @cpu = conf["cpu"].to_i
      @ram = conf["ram"].to_i

      raise ArgumentError("Missing project for box") if @project.nil?
      raise ArgumentError("Missing index for box") if @index.nil?
      raise ArgumentError("Missing name for box") if @name.nil? || @name == ""
      raise ArgumentError("Boxes need at least 1024MB of memory") if @ram < 1024

      @logger = Log4r::Logger.new("aeriscloud::box::#{@name}")
    end

    # The virtualbox configuration
    def config()
      return {
        :memory => @ram,
        :cpus => @cpu,
        # BIOS setup
        :bioslogodisplaytime => Environment::GUI_ENABLED ? 10000 : 10,
        :bioslogoimagepath => "#{Environment::AERISCLOUD_PATH}/docs/images/aeris.bmp",
        :bioslogofadein => "off",
        :bioslogofadeout => "off",
        # Enable advanced CPU features
        :ioapic => "on",
        :hpet => "on",
        :nestedpaging => "on",
        :largepages => "on",
        :pae => "on",
        :hwvirtex => "on",
        :vtxvpid => "on",
        :vtxux => "on",
        # Disable GPU acceleration
        :accelerate3d => "off",
        :accelerate2dvideo => "off",
        :vram => "9",
        # Disable NAT proxies
        :natdnsproxy1 => "off",
        :natdnsproxy2 => "off",
        # Use virtio for net interfaces
        :nictype1 => "virtio",
        :nictype2 => "virtio",
      }
    end

    def disk_path()
      "#{Environment::DISKS_PATH}/#{vm_name}-data.vdi"
    end

    # IPs start at index+2 so that we get 172.16.<id>.2,
    # then .3, etc... (.1 is for the router)
    def ip()
      "172.16.#{@project.id}.#{@index + 2}"
    end

    def broadcast()
      "172.16.#{@project.id}.255"
    end

    def netmask()
      "255.255.255.0"
    end

    def forwards()
      return {
        :ssh => { :src => 22, :dest => @project.id * 20 + 20001 + @index },
        :web => { :src => 80, :dest => @project.id * 20 + 30001 + @index }
      }
    end

    def private_key()
      pkey = "~/.vagrant.d/insecure_private_key"
      # This only works on Ruby 1.9+
      if Gem::Version.new(Vagrant::VERSION) >= Gem::Version.new('1.7.0')
        pkey = File.join('.vagrant/machines', @name, 'virtualbox/private_key')
      end
      return File.expand_path(pkey)
    end

    def vm_name()
      "#{@project.name}-#{@name}"
    end

    def primary?()
      @index == 0
    end

    def provision?()
      @conf["provision"].nil? ? true : @conf["provision"]
    end

    # Run the rsync command
    def rsync!()
      return if !@project.rsync?

      doSync = true
      ssh_cmd = "ssh -l vagrant -i #{private_key}"

      if system "#{ssh_cmd} #{ip} '[ -d /data ]'" && $? == 0
        data_dir = "/data/#{@project.name}"
        project_dir = "/home/vagrant/#{@project.name}"

        @logger.info "Syncing your project directory to the box's data directory (#{project_dir})"

        system "#{ssh_cmd} #{box.ip} 'sudo mkdir -p #{data_dir} && sudo chown vagrant.vagrant #{data_dir}'"
        system "rsync --archive --hard-links --one-file-system --delete #{box.rsync_ignores} --compress-level=0 "\
            "--omit-dir-times -e '#{ssh_cmd} -T -c arcfour -o Compression=no -x' ./ #{box.ip}:#{data_dir}/"
        system "#{ssh_cmd} #{box.ip} 'mkdir -p #{project_dir} && sudo mount -o bind #{data_dir} #{project_dir}'"
      else
        @logger.info "/data disk not mounted and formatted yet. Skipping sync for now."
      end
    end
  end
end
