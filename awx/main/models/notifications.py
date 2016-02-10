# Copyright (c) 2016 Ansible, Inc.
# All Rights Reserved.

import logging

from django.db import models
from django.core.urlresolvers import reverse
from django.core.mail.message import EmailMessage
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_str

from awx.main.models.base import * # noqa
from awx.main.notifications.email_backend import CustomEmailBackend
from awx.main.notifications.slack_backend import SlackBackend
from awx.main.notifications.twilio_backend import TwilioBackend

# Django-JSONField
from jsonfield import JSONField

logger = logging.getLogger('awx.main.models.notifications')

__all__ = ['NotificationTemplate', 'Notification']

class NotificationTemplate(CommonModel):

    NOTIFICATION_TYPES = [('email', _('Email'), CustomEmailBackend),
                          ('slack', _('Slack'), SlackBackend),
                          ('twilio', _('Twilio'), TwilioBackend)]
    NOTIFICATION_TYPE_CHOICES = [(x[0], x[1]) for x in NOTIFICATION_TYPES]
    CLASS_FOR_NOTIFICATION_TYPE = dict([(x[0], x[2]) for x in NOTIFICATION_TYPES])

    class Meta:
        app_label = 'main'

    organization = models.ForeignKey(
        'Organization',
        blank=False,
        null=True,
        on_delete=models.SET_NULL,
        related_name='notification_templates',
    )

    notification_type = models.CharField(
        max_length = 32,
        choices=NOTIFICATION_TYPE_CHOICES,
    )

    notification_configuration = JSONField(blank=False)

    def get_absolute_url(self):
        return reverse('api:notification_template_detail', args=(self.pk,))

    @property
    def notification_class(self):
        return self.CLASS_FOR_NOTIFICATION_TYPE[self.notification_type]

    @property
    def recipients(self):
        return self.notification_configuration[self.notification_class.recipient_parameter]

    def generate_notification(self, subject, message):
        notification = Notification(notifier=self,
                                    notification_type=self.notification_type,
                                    recipients=smart_str(self.recipients),
                                    subject=subject,
                                    body=message)
        notification.save()
        return notification

    def send(self, subject, body):
        recipients = self.notification_configuration.pop(self.notification_class.recipient_parameter)
        sender = self.notification_configuration.pop(self.notification_class.sender_parameter, None)
        backend_obj = self.notification_class(**self.notification_configuration)
        notification_obj = EmailMessage(subject, body, sender, recipients)
        return backend_obj.send_messages([notification_obj])

class Notification(CreatedModifiedModel):
    '''
    A notification event emitted when a Notifier is run
    '''

    NOTIFICATION_STATE_CHOICES = [
        ('pending', _('Pending')),
        ('successful', _('Successful')),
        ('failed', _('Failed')),
    ]

    class Meta:
        app_label = 'main'
        ordering = ('pk',)

    notifier = models.ForeignKey(
        'NotificationTemplate',
        related_name='notifications',
        on_delete=models.CASCADE,
        editable=False
    )
    status = models.CharField(
        max_length=20,
        choices=NOTIFICATION_STATE_CHOICES,
        default='pending',
        editable=False,
    )
    error = models.TextField(
        blank=True,
        default='',
        editable=False,
    )
    notifications_sent = models.IntegerField(
        default=0,
        editable=False,
    )
    notification_type = models.CharField(
        max_length = 32,
        choices=NotificationTemplate.NOTIFICATION_TYPE_CHOICES,
    )
    recipients = models.TextField(
        blank=True,
        default='',
        editable=False,
    )
    subject = models.TextField(
        blank=True,
        default='',
        editable=False,
    )
    body = models.TextField(
        blank=True,
        default='',
        editable=False,
    )
    
    def get_absolute_url(self):
        return reverse('api:notification_detail', args=(self.pk,))
