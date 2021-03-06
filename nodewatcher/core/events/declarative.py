import collections
import copy
import uuid

from django.core import exceptions

from . import base as events_base
from ..registry import registration

# Randomly generated UUID for generating UUIDs for uniquely identifying events.
EVENT_UUID_NAMESPACE = uuid.UUID('766d8c80-17e8-4778-af77-d5eee53bca05')


class Attribute(object):
    """
    Node event attributes are used to declare what tags an event
    class provides, so this information can be available to filter
    implementations.
    """

    _creation_order = 0

    def __init__(self, primary_key=False):
        """
        Class constructor.
        """

        self.name = None
        self.primary_key = primary_key
        self._order = Attribute._creation_order
        Attribute._creation_order += 1

    def get_form_field(self):
        """
        Returns the form field that can be used to configure a filter for
        this attribute.
        """

        pass

    def __repr__(self):
        return "<Attribute '%s'>" % self.name


class CharAttribute(Attribute):
    """
    String attribute.
    """

    def get_form_field(self):
        """
        Returns the form field that can be used to configure a filter for
        this attribute.
        """

        # TODO: Return a proper form field
        pass


class ChoiceAttribute(CharAttribute):
    """
    Enumeration attribute.
    """

    def __init__(self, regpoint, enum_id, **kwargs):
        """
        Class constructor.

        :param regpoint: Registration point name
        :param enum_id: Enumeration identifier
        """

        self.regpoint = regpoint
        self.enum_id = enum_id
        self.choices = registration.point(regpoint).get_registered_choices(enum_id).field_tuples()
        super(ChoiceAttribute, self).__init__(**kwargs)

    def get_form_field(self):
        """
        Returns the form field that can be used to configure a filter for
        this attribute.
        """

        # TODO: Return a select form field
        pass


class NodeEventRecordMeta(type):
    def __new__(cls, classname, bases, attrs):
        """
        Constructs a new streams descriptor type.
        """

        if classname in ('NodeEventRecord', 'NodeWarningRecord'):
            return type.__new__(cls, classname, bases, attrs)

        # Create the actual class
        module = attrs.pop("__module__")
        new_class = type.__new__(cls, classname, bases, {"__module__": module})
        new_class._attributes = collections.OrderedDict()

        # Ensure that source_name and source_type are set
        if attrs.get('source_name', None) is None:
            attrs['source_name'] = module
        if attrs.get('source_type', None) is None:
            attrs['source_type'] = classname

        # Inherit all attributes from parent classes
        for base in bases:
            if not hasattr(base, '_attributes'):
                continue

            for name, value in sorted(base._attributes.items(), key=lambda p: getattr(p[1], '_order', -1)):
                if not isinstance(value, Attribute):
                    continue

                if name in new_class._attributes:
                    raise exceptions.ImproperlyConfigured("Duplicate attribute '%s' in event record '%s'!" % (name, classname))

                value = copy.deepcopy(value)
                new_class._attributes[name] = value

        # Add all attributes to our event record class
        for name, value in sorted(attrs.items(), key=lambda p: getattr(p[1], '_order', -1)):
            if not isinstance(value, Attribute):
                setattr(new_class, name, value)
                continue

            if name in new_class._attributes:
                raise exceptions.ImproperlyConfigured("Duplicate attribute '%s' in event record '%s'!" % (name, classname))

            value.name = name
            new_class._attributes[name] = value

        return new_class


class NodeEventRecord(events_base.EventRecord):
    """
    Base class for node event records.
    """

    __metaclass__ = NodeEventRecordMeta

    source_name = None
    source_type = None
    description = None

    SEVERITY_INFO = 1
    SEVERITY_WARNING = 2
    SEVERITY_ERROR = 3

    def __init__(self, related_nodes, severity, related_users=None, **kwargs):
        """
        Class constructor.

        :param related_nodes: A list of related node instances
        :param severity: Event severity
        :param related_users: Optional list of user instances related to this event
        """

        if not isinstance(related_nodes, (tuple, list)):
            related_nodes = [related_nodes]

        if related_users is not None and not isinstance(related_users, (tuple, list)):
            related_users = [related_users]

        super(NodeEventRecord, self).__init__(
            related_nodes=related_nodes,
            severity=severity,
            source_name=self.source_name,
            source_type=self.source_type,
            related_users=related_users,
            **kwargs
        )

    @classmethod
    def get_attributes(cls):
        """
        Returns a list of all attribute descriptors for this event class.
        """

        return cls._attributes.values()

    @classmethod
    def get_attribute(cls, name):
        """
        Returns a specific attribute.

        :param name: Attribute name
        :return: Attribute instance
        """

        return cls._attributes[name]

    @classmethod
    def get_description(cls, data):
        """
        Generates a localized event-description from event data.

        :param data: Event data dictionary
        """

        if cls.description is not None:
            return cls.description % data

        raise exceptions.ImproperlyConfigured("Event description not set.")

    @classmethod
    def get_url(cls, data):
        """
        Returns an URL that one should be redirected to when wanting to
        see the details about this event. The default implementation always
        returns None.

        :param data: Event data dictionary
        """

        pass

    def get_primary_key(self):
        """
        Returns an UUID value uniquely identifying this specific event.
        """

        primary_key = [
            self.source_type,
            self.source_name,
        ]

        for node in self.related_nodes:
            primary_key.append(str(node.uuid))

        for attribute in self.get_attributes():
            if not attribute.primary_key:
                continue

            primary_key.append(str(getattr(self, attribute.name, None)))

        return uuid.uuid5(EVENT_UUID_NAMESPACE, ','.join(primary_key))


class NodeWarningRecord(NodeEventRecord):
    """
    Base class for node warning records.
    """

    def __init__(self, related_nodes, severity, **kwargs):
        """
        Class constructor.

        :param related_nodes: A list of related node instances
        :param severity: Warning severity
        """

        super(NodeWarningRecord, self).__init__(
            related_nodes=related_nodes,
            severity=severity,
            **kwargs
        )
