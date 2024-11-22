# Copyright 2024 Hewlett Packard Enterprise Development LP
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
"""A driver module that wraps the libvirtdriver module allowing
libvirt domain names to be used instead of domain UUIDs to identify
and enumerate 'systems' (domains) in control of an instance of Sushy
Tools.

"""

from inspect import getfullargspec

# Even though we don't use it here, 'is_loaded' can be imported by
# users of this driver to determine whether libvirt is loaded in the
# base driver. That is implemented in the libvirtdriver, not
# here. Importing it here passes it through to users of this driver.
#
# pylint: disable=unused-import
from .libvirtdriver import (
    is_loaded,
    libvirt_open,
    LibvirtDriver as DriverBase
)
from ....error import AliasAccessError

def wrapped_identity(func):
    """A decorator function used to wrap calls that raise an
    AliasAccessError to cause a REST API redirect when the function is
    called with an 'identity' argument whose contents specify a domain
    name instead of a UUID as the domain identifier. The wrapper
    performs the redirection under the covers so that the caller can
    use domain names without seeing a difference. The wrapped function
    is called first with whatever 'identity' the caller provided. If
    that is an active domain UUID, then no further work is needed and
    the result is simply returned. If the call raises an
    AliasAccessError, however, the wrapper calls the function again
    with 'identity' coerced to the UUID found in the
    AliasAccessError. Any other error is simply allowed to bubble up
    to the caller.

    :param func: the function to be decorated

    """

    def identity_wrapper(*args, **kwargs):
        """The wrapper for the decorator which handles the
        redirection.

        :param args: positional arguments supplied by the caller collapsed in the call
        :param kwargs: keyword arguments supplied by the caller collapsed in the call
        :returns: the return value of the wrapped function

        """
        # We need the list of function arguments to do the coercion and we
        # need to make sure there is an 'identity' argument anyway, so
        # pick this up here.
        arguments = getfullargspec(func).args
        if 'identity' not in arguments:
            raise ValueError(
                "functions decorated by 'wrapped_identity' must take "
                "an argument named 'identity'"
            )
        # We want all of the arguments as keyword arguments so we can
        # update the 'identity' argument as needed. This will move
        # all of the arguments passed in into kwargs so they can be
        # passed to the wrapped function.
        kwargs.update(dict(zip(arguments, args)))
        args = ()
        try:
            return func(*args, **kwargs)
        except AliasAccessError as err:
            kwargs['identity'] = str(err)
            return func(*args, **kwargs)
    return identity_wrapper

# pylint: disable=too-many-public-methods
class LibvirtDriver(DriverBase):
    """A driver class that handles libvirt domains by name instead of
    strictly by UUID. This is a thin wrapper for the LibvirtDriver
    class (from which it inherits) which handles redirects resulting
    from domain name targeted queries and provides a list of domains
    by name instead of UUID to the caller.

    """
    @property
    def driver(self):
        """Overrides the LibvirtDriver with a different driver name.
        :returns: driver information as string
        """
        return '<libvirtbyname>'

    @property
    def systems(self):
        """Return available computer systems by name

        :returns: list of domain names representing the systems
        """
        with libvirt_open(self._uri, readonly=True) as conn:
            return [domain.name() for domain in conn.listAllDomains()]

    @wrapped_identity
    def uuid(self, identity):
        """Get computer system UUID

        The universal unique identifier (UUID) for this system. Can be used
        in place of system name if there are duplicates.

        :param identity: libvirt domain name or UUID
        :raises: NotFound if the system cannot be found
        :returns: computer system UUID
        """
        return super().uuid(identity)

    @wrapped_identity
    def name(self, identity):
        """Get computer system name by name

        :param identity: libvirt domain name or UUID
        :raises: NotFound if the system cannot be found
        :returns: computer system name
        """
        return super().name(identity)

    @wrapped_identity
    def get_power_state(self, identity):
        """Get computer system power state

        :param identity: libvirt domain name or ID

        :returns: current power state as *On* or *Off* `str` or `None`
            if power state can't be determined
        """
        return super().get_power_state(identity)

    @wrapped_identity
    def set_power_state(self, identity, state):
        """Set computer system power state

        :param identity: libvirt domain name or ID
        :param state: string literal requesting power state transition.
            Valid values  are: *On*, *ForceOn*, *ForceOff*, *GracefulShutdown*,
            *GracefulRestart*, *ForceRestart*, *Nmi*.

        :raises: `error.FishyError` if power state can't be set
        """
        return super().set_power_state(identity, state)

    @wrapped_identity
    def get_boot_device(self, identity):
        """Get computer system boot device name

        First try to get boot device from bootloader configuration.. If it's
        not present, proceed towards gathering boot order information from
        per-device boot configuration, then pick the lowest ordered device.

        :param identity: libvirt domain name or ID

        :returns: boot device name as `str` or `None` if device name
            can't be determined
        """
        return super().get_boot_device(identity)

    @wrapped_identity
    def set_boot_device(self, identity, boot_source):
        """Get/Set computer system boot device name

         First remove all boot device configuration from bootloader
         because that's legacy with libvirt. Then remove possible boot
         configuration in the per-device settings. Finally, make the
         desired boot device the only bootable by means of per-device
         configuration boot option.

        :param identity: libvirt domain name or ID
            :param boot_source: string literal requesting boot device
            change on the system. Valid values are: *Pxe*, *Hdd*, *Cd*.

        :raises: `error.FishyError` if boot device can't be set

        """
        return super().set_boot_device(identity, boot_source)

    @wrapped_identity
    def get_boot_mode(self, identity):
        """Get computer system boot mode.

        :param identity: libvirt domain name or ID

        :returns: either *UEFI* or *Legacy* as `str` or `None` if
            current boot mode can't be determined
        """
        return super().get_boot_mode(identity)

    @wrapped_identity
    def set_boot_mode(self, identity, boot_mode):
        """Set computer system boot mode.

        :param identity: libvirt domain name or ID

        :param boot_mode: string literal requesting boot mode
            change on the system. Valid values are: *UEFI*, *Legacy*.

        :raises: `error.FishyError` if boot mode can't be set
        """
        return super().set_boot_mode(identity, boot_mode)

    @wrapped_identity
    def get_secure_boot(self, identity):
        """Get computer system secure boot state for UEFI boot mode.

        :returns: boolean of the current secure boot state

        :raises: `FishyError` if the state can't be fetched
        """
        return super().get_secure_boot(identity)

    @wrapped_identity
    def set_secure_boot(self, identity, secure):
        """Set computer system secure boot state for UEFI boot mode.

        :param secure: boolean requesting the secure boot state

        :raises: `FishyError` if the can't be set
        """
        return super().set_secure_boot(identity, secure)

    @wrapped_identity
    def get_total_memory(self, identity):
        """Get computer system total memory

        :param identity: libvirt domain name or ID

        :returns: available RAM in GiB as `int` or `None` if total memory
            count can't be determined
        """
        return super().get_total_memory(identity)

    @wrapped_identity
    def get_total_cpus(self, identity):
        """Get computer system total count of available CPUs

        :param identity: libvirt domain name or ID

        :returns: available CPU count as `int` or `None` if CPU count
            can't be determined
        """
        return super().get_total_cpus(identity)

    @wrapped_identity
    def get_bios(self, identity):
        """Get BIOS section

        If there are no BIOS attributes, domain is updated with default values.

        :param identity: libvirt domain name or ID
        :returns: dict of BIOS attributes
        """
        return super().get_bios(identity)

    @wrapped_identity
    def get_versions(self, identity):
        """Get firmware versions section

        If there are no firmware version attributes, domain is updated with
        default values.

        :param identity: libvirt domain name or ID
        :returns: dict of firmware version attributes
        """
        return super().get_versions(identity)

    @wrapped_identity
    def set_bios(self, identity, attributes):
        """Update BIOS attributes

        These values do not have any effect on VM. This is a workaround
        because there is no libvirt API to manage BIOS settings.
        By storing fake BIOS attributes they are attached to VM and are
        persisted through VM lifecycle.

        Updates to attributes are immediate unlike in real BIOS that
        would require system reboot.

        :param identity: libvirt domain name or ID
        :param attributes: dict of BIOS attributes to update. Can pass only
            attributes that need update, not all
        """
        return super().set_bios(identity, attributes)

    @wrapped_identity
    def set_versions(self, identity, firmware_versions):
        """Update firmware versions

        These values do not have any effect on VM. This is a workaround
        because there is no libvirt API to manage firmware versions.
        By storing fake firmware versions they are attached to VM and are
        persisted through VM lifecycle.

        Updates to versions are immediate unlike in real firmware that
        would require system reboot.

        :param identity: libvirt domain name or ID
        :param firmware_versions: dict of firmware versions to update.
            Can pass only versions that need update, not all
        """
        return super().set_versions(identity, firmware_versions)

    @wrapped_identity
    def reset_bios(self, identity):
        """Reset BIOS attributes to default

        :param identity: libvirt domain name or ID
        """
        return super().reset_bios(identity)

    @wrapped_identity
    def reset_versions(self, identity):
        """Reset firmware versions to default

        :param identity: libvirt domain name or ID
        """
        return super().reset_versions(identity)

    @wrapped_identity
    def get_nics(self, identity):
        """Get list of network interfaces and their MAC addresses

        Use MAC address as network interface's id

        :param identity: libvirt domain name or ID

        :returns: list of network interfaces dict with their attributes
        """
        return super().get_nics(identity)

    @wrapped_identity
    def get_processors(self, identity):
        """Get list of processors

        :param identity: libvirt domain name or ID

        :returns: list of processors dict with their attributes
        """
        return super().get_processors(identity)

    @wrapped_identity
    def get_boot_image(self, identity, device):
        """Get backend VM boot image info

        :param identity: libvirt domain name or ID
        :param device: device type (from
            `sushy_tools.emulator.constants`)
        :returns: a `tuple` of (boot_image, write_protected, inserted)
        :raises: `error.FishyError` if boot device can't be accessed
        """
        return super().get_boot_image(identity, device)

    @wrapped_identity
    def set_boot_image(self, identity, device, boot_image=None,
                       write_protected=True):
        """Set backend VM boot image

        :param identity: libvirt domain name or ID
        :param device: device type (from
            `sushy_tools.emulator.constants`)
        :param boot_image: path to the image file or `None` to remove
            configured image entirely
        :param write_protected: expose media as read-only or writable

        :raises: `error.FishyError` if boot device can't be set
        """
        return super().set_boot_image(
            identity, device, boot_image, write_protected
        )

    @wrapped_identity
    def get_simple_storage_collection(self, identity):
        """Get a dict of simple storage controllers and their devices

        Only those storage devices that are configured as a libvirt volume
        via a pool and attached to the domain will reflect as a device.
        Others are skipped.

        :param identity: libvirt domain or ID
        :returns: dict of simple storage controller dict with their attributes
        """
        return super().get_simple_storage_collection(identity)

    @wrapped_identity
    def get_http_boot_uri(self, identity):
        """Return the URI stored for the HttpBootUri.

        :param identity: The libvirt identity. Unused, exists for internal
                         sushy-tools compatibility.
        :returns: Stored URI value for HttpBootURI.
        """
        return super().get_http_boot_uri(identity)
