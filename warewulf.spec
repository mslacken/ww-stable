%global debug_package %{nil}

%global api 1
%if 0%{?rhel} && 0%{?rhel} <= 7
%global api 0
%endif

%if 0%{?suse_version}
%global tftpdir /srv/tftpboot
%else
# Assume Fedora-based OS if not SUSE-based
%global tftpdir /var/lib/tftpboot
%endif
%global srvdir %{_sharedstatedir}

%global wwgroup warewulf

%if 0%{?fedora}
%define _build_id_links none
%endif


Name: warewulf
Summary: A provisioning system for large clusters of bare metal and/or virtual systems
Version: 4.5.1
Release: 0
License: BSD-3-Clause
URL:     https://github.com/warewulf/warewulf
#!RemoteAsset
Source:  https://github.com/warewulf/warewulf/releases/download/v%{version}/warewulf-%{version}.tar.gz

ExclusiveOS: linux

Conflicts: warewulf < 4
Conflicts: warewulf-common
Conflicts: warewulf-cluster
Conflicts: warewulf-vnfs
Conflicts: warewulf-provision
Conflicts: warewulf-ipmi

%if 0%{?suse_version} || 0%{?sle_version}
BuildRequires: distribution-release
BuildRequires: systemd-rpm-macros
BuildRequires: go >= 1.16
BuildRequires: firewall-macros
BuildRequires: firewalld
BuildRequires: tftp
BuildRequires: yq
Requires: tftp
Requires: nfs-kernel-server
Requires: firewalld
Requires: ipxe-bootimgs
%else
# Assume Red Hat/Fedora build
BuildRequires: system-release
BuildRequires: systemd
BuildRequires: golang >= 1.20
BuildRequires: firewalld-filesystem
Requires: tftp-server
Requires: nfs-utils
%if 0%{?rhel} < 8
Requires: ipxe-bootimgs
%else
Requires: ipxe-bootimgs-x86
Requires: ipxe-bootimgs-aarch64
%endif
%endif

%if 0%{?rhel} >= 8 || 0%{?suse_version} || 0%{?fedora}
Requires: dhcp-server
%else
# rhel < 8
Requires: dhcp
%endif

BuildRequires: git
BuildRequires: make
%if %{api}
BuildRequires: libassuan-devel gpgme-devel
%endif

%description
Warewulf is a stateless and diskless container operating system provisioning
system for large clusters of bare metal and/or virtual systems.


%prep
%setup -q -n %{name}-%{version} -b0 %if %{?with_offline:-a2}


%build
export OFFLINE_BUILD=1
make defaults \
    PREFIX=%{_prefix} \
    BINDIR=%{_bindir} \
    SYSCONFDIR=%{_sysconfdir} \
    DATADIR=%{_datadir} \
    LOCALSTATEDIR=%{_sharedstatedir} \
    SHAREDSTATEDIR=%{_sharedstatedir} \
    MANDIR=%{_mandir} \
    INFODIR=%{_infodir} \
    DOCDIR=%{_docdir} \
    SRVDIR=%{srvdir} \
    TFTPDIR=%{tftpdir} \
    SYSTEMDDIR=%{_unitdir} \
    BASHCOMPDIR=/etc/bash_completion.d/ \
    FIREWALLDDIR=/usr/lib/firewalld/services \
    WWCLIENTDIR=/warewulf \
    IPXESOURCE=/usr/share/ipxe
make
%if %{api}
make api
%endif


%install
export OFFLINE_BUILD=1
export NO_BRP_STALE_LINK_ERROR=yes
make install \
    DESTDIR=%{buildroot}
%if %{api}
make installapi \
    DESTDIR=%{buildroot}
%endif

%if 0%{?suse_version} || 0%{?sle_version}
yq e '
  .tftp.ipxe."00:00" = "undionly.kpxe" |
  .tftp.ipxe."00:07" = "ipxe-x86_64.efi" |
  .tftp.ipxe."00:09" = "ipxe-x86_64.efi" |
  .tftp.ipxe."00:0B" = "snp-arm64.efi" ' \
  -i %{buildroot}%{_sysconfdir}/warewulf/warewulf.conf
%endif

%pre
getent group %{wwgroup} >/dev/null || groupadd -r %{wwgroup}
# use ipxe images from the distribution


%post
%systemd_post warewulfd.service
%firewalld_reload


%preun
%systemd_preun warewulfd.service


%postun
%systemd_postun_with_restart warewulfd.service
%firewalld_reload


%files
%defattr(-, root, %{wwgroup})
%dir %{_sysconfdir}/warewulf
%config(noreplace) %{_sysconfdir}/warewulf/warewulf.conf
%config(noreplace) %{_sysconfdir}/warewulf/examples
%config(noreplace) %{_sysconfdir}/warewulf/ipxe
%config(noreplace) %{_sysconfdir}/warewulf/grub
%config(noreplace) %attr(0640,-,-) %{_sysconfdir}/warewulf/nodes.conf
%{_sysconfdir}/bash_completion.d/wwctl

%dir %{_sharedstatedir}/warewulf
%{_sharedstatedir}/warewulf/chroots
%dir %{_sharedstatedir}/warewulf/overlays
%dir %{_sharedstatedir}/warewulf/overlays/debug
%dir %{_sharedstatedir}/warewulf/overlays/generic
%dir %{_sharedstatedir}/warewulf/overlays/host
%dir %{_sharedstatedir}/warewulf/overlays/wwinit
%attr(-, root, root) %{_sharedstatedir}/warewulf/overlays/*/rootfs

%attr(-, root, root) %{_bindir}/wwctl
%attr(-, root, root) %{_prefix}/lib/firewalld/services/warewulf.xml
%attr(-, root, root) %{_unitdir}/warewulfd.service
%attr(-, root, root) %{_mandir}/man1/wwctl*
%attr(-, root, root) %{_mandir}/man5/*.5*
%attr(-, root, root) %{_datadir}/warewulf

%dir %{_docdir}/warewulf
%license %{_docdir}/warewulf/LICENSE.md

%if %{api}
%attr(-, root, root) %{_bindir}/wwapi*
%config(noreplace) %{_sysconfdir}/warewulf/wwapi*.conf
%endif


%changelog
* Wed Apr 17 2024 Jonathon Anderson <janderson@ciq.com>
- Don't build the API on EL7

* Sat Mar 9 2024 Jonathon Anderson <janderson@ciq.com> - 4.5.0-1
- Update source to github.com/warewulf
- Fix ownership of overlay files
- Add packaging for new grub support
- Add dependencies on distribution ipxe packages
- Fix offline builds
- Accommodate new Makefile behavior
- Designate config files in /etc/warewulf/ as "noreplace"
- Updated path to shell completions

* Mon Oct 17 2022 Jeremy Siadal <jeremy.c.siadal@intel.com> - 4.4.0-1
- Add offline build support -- prepping for bcond
- Add more BuildRequires for new golang vendor modules

* Wed Jan 26 2022 Jeremy Siadal <jeremy.c.siadal@intel.com> - 4.2.0-1
- Add license install
- Updates for RH and SUSE RPM guidelines

* Sat Jan 15 2022 Gregory Kurtzer <gmkurtzer@gmail.com> - 4.2.0-1
- Integrated genconfig Make options
- Cleaned up SPEC to use default RPM macros

* Tue Jan 11 2022 Jeremy Siadal <jeremy.c.siadal@intel.com> - 4.2.0-1
- Merge overlay subdirectories
- Add configuration options to make
- Relocate tftpboot for OpenSUSE
- Remove libexecdir macro; changing in OpenSUSE 15.4

* Mon Nov 1 2021 Jeremy Siadal <jeremy.c.siadal@intel.com> - 4.2.0-1
- Add support for OpenSUSE
- Update file attribs
- Update license string
- Make shared store relocatable

* Fri Sep 24 2021 Michael L. Young <myoung@ciq.com> - 4.2.0-1
- Update spec file to use systemd macros
- Use macros to refer to system paths
- Update syntax

* Tue Jan 26 2021 14:46:24 JST Brian Clemens <bclemens@ciq.com> - 4.0.0
- Initial release
