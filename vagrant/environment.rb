module AerisCloud
  module Environment
    AERISCLOUD_PATH = ENV['AERISCLOUD_PATH'].nil? ? "/opt/aeriscloud" : File.expand_path(ENV['AERISCLOUD_PATH'])
    DISKS_PATH = ENV['VAGRANT_DISKS_PATH']
    ORGANIZATION = ENV['AERISCLOUD_DEFAULT_ORGANIZATION'] || ""
    ORGANIZATIONS_PATH = ENV['AERISCLOUD_ORGANIZATIONS_DIR'] || ""

    # VM configuration
    GUI_ENABLED = ENV['GUI'].nil? ? false : true

    # Ansible configuration
    ANSIBLE_DEBUG = ENV['DEBUG'].nil? ? false : ENV['DEBUG']
    ANSIBLE_TAGS = ENV['tags']
    ANSIBLE_SKIP_TAGS = ENV['skip_tags']

    # NFS options
    NFS_MOUNT_OPTIONS =  [
      'fsc', 'vers=3', 'tcp', 'nosuid', 'nodev', 'noatime', 'nodiratime', 'nolock', 'async',
      'rsize=65536', 'wsize=65536', 'intr', 'acregmin=6', 'acregmax=120', 'acdirmin=60', 'acdirmax=120'
    ]

    # Extras
    DEBUG = ENV['debug'].nil? ? false : ENV['debug']
    GITCONFIG_PATH = ENV['GITCONFIG'].nil? ? "#{Dir.home}/.gitconfig" : ENV['GITCONFIG']
    GITCONFIG = File.file?(GITCONFIG_PATH) ? IO.read(GITCONFIG_PATH) : ""
  end
end