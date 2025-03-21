import abc
import csv
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.views.generic import DetailView, ListView, TemplateView
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.edit import ModelFormMixin, ProcessFormView, UpdateView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from chipy_org.libs.permissions_classes import IsAPIUser

from .forms import RSVPForm, RSVPFormWithCaptcha
from .models import RSVP as RSVPModel
from .models import Meeting
from .serializers import MeetingSerializer
from .utils import meetup_meeting_sync

logger = logging.getLogger(__name__)


class InitialRSVPMixin(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def get_meeting(self):
        # override this method to determine the meeting used for the rsvp
        # the function is expected to return a single Meeting object
        raise NotImplementedError("Must implement 'get_meeting'")

    def get_initial(self, meeting):
        initial = {"response": "Y"}
        initial.update({"meeting": meeting})
        if self.request.user.is_authenticated:
            user = self.request.user
            user_data = {
                "user": user,
                "email": getattr(user, "email", None),
                "first_name": getattr(user, "first_name", None),
                "last_name": getattr(user, "last_name", None),
            }
            initial.update(user_data)
        self.initial = initial

    def get_form_class(self):
        if self.request.user.is_authenticated:
            return RSVPForm
        else:
            return RSVPFormWithCaptcha

    def get_form(self, **kwargs):
        form_class = self.get_form_class()
        return form_class(**kwargs)

    def add_extra_context(self, context):
        meeting = self.get_meeting()
        context["next_meeting"] = meeting

        if meeting:
            self.get_initial(meeting)
            context["form"] = self.get_form(request=self.request, initial=self.initial)

            if self.request.user.is_authenticated:
                context["rsvp"] = RSVPModel.objects.filter(
                    meeting=meeting, user=self.request.user
                ).first()
        return context


class FutureMeetings(ListView):
    template_name = "meetings/future_meetings.html"
    queryset = Meeting.objects.future_published()
    paginate_by = 5


class MeetingStatus(PermissionRequiredMixin, ListView):
    permission_required = "meetings.view_meeting"

    def handle_no_permission(self):
        return redirect(reverse_lazy("home"))

    template_name = "meetings/meetings_status.html"
    queryset = Meeting.objects.future_published_main()


class PastMeetings(ListView):
    template_name = "meetings/past_meetings.html"
    queryset = Meeting.objects.past_published()
    paginate_by = 5


class MeetingDetail(DetailView, InitialRSVPMixin):
    template_name = "meetings/meeting.html"
    pk_url_kwarg = "pk"
    model = Meeting

    def get_meeting(self):
        return self.object

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(kwargs)
        context = self.add_extra_context(context)
        return context


class RSVP(ProcessFormView, ModelFormMixin, TemplateResponseMixin):
    http_method_names = ["post", "get"]
    success_url = reverse_lazy("home")

    def get_template_names(self):
        if self.request.method == "POST":
            return ["meetings/_rsvp_form_response.html"]
        elif self.request.method == "GET":
            return ["meetings/rsvp_form.html"]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"request": self.request})
        return kwargs

    def dispatch(self, request, *args, **kwargs):
        self.object = None

        def lookup_meeting():
            if self.request.method == "POST":
                meeting_id = self.request.POST.get("meeting", None)

            if self.request.method == "GET":
                meeting_id = self.request.GET.get("meeting", None)

            if not meeting_id:
                raise Http404("Meeting missing from POST")

            try:
                meeting_id = int(meeting_id)
            except (ValueError, TypeError) as ex:
                raise Http404("The meeting must be an integer") from ex

            return get_object_or_404(Meeting, pk=meeting_id)

        self.meeting = lookup_meeting()

        if self.request.user.is_authenticated:
            try:
                self.object = RSVPModel.objects.get(user=self.request.user, meeting=self.meeting)
            except RSVPModel.DoesNotExist:
                pass

        # check to see if registration is closed
        if not self.meeting.can_register():
            messages.error(request, "Registration for this meeting is closed.")
            return redirect(reverse_lazy("home"))

        return super().dispatch(request, *args, **kwargs)

    def get_form_class(self):
        authenticated = self.request.user.is_authenticated
        return RSVPForm if authenticated else RSVPFormWithCaptcha

    def form_valid(self, form):
        # calling super.form_valid(form) also does self.object = form.save()
        response = super().form_valid(form)
        status = self.object.get_status_display().upper()
        msg = f"Your RSVP has been {status}."

        if self.object.status == RSVPModel.Statuses.CONFIRMED:
            messages.success(self.request, msg)
        else:
            messages.warning(self.request, msg)
        return response

    def get_initial(self):
        initial = {
            "meeting": self.meeting,
            "response": "Y",
        }
        if self.request.user.is_authenticated:
            user = self.request.user
            data = {
                "user": user,
                "email": getattr(user, "email", None),
                "first_name": getattr(user, "first_name", None),
                "last_name": getattr(user, "last_name", None),
            }
            initial.update(data)
        return initial


class UpdateRSVP(UpdateView):
    model = RSVPModel
    form_class = RSVPForm
    success_url = reverse_lazy("home")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self.object.meeting.can_register():
            messages.error(
                self.request,
                "Registration for this meeting on is closed.",
            )
            return HttpResponseRedirect(reverse_lazy("home"))
        return self.render_to_response(self.get_context_data())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"request": self.request})
        return kwargs

    def form_valid(self, form):
        if self.request.method == "POST":
            messages.success(self.request, "RSVP updated succesfully.")
        return super().form_valid(form)

    def get_object(self, queryset=None):
        obj = get_object_or_404(RSVPModel, key=self.kwargs["rsvp_key"])
        return obj

    def get_template_names(self):
        if self.request.method == "POST":
            return ["meetings/_rsvp_form_response.html"]
        elif self.request.method == "GET":
            return ["meetings/rsvp_form.html"]


class RSVPlist(ListView):
    context_object_name = "attendees"
    template_name = "meetings/rsvp_list.html"

    def get_queryset(self):
        self.meeting = get_object_or_404(Meeting, key=self.kwargs["meeting_key"])
        return (
            RSVPModel.objects.filter(meeting=self.meeting)
            .exclude(response="N")
            .filter(response=RSVPModel.Responses.IN_PERSON, status=RSVPModel.Statuses.CONFIRMED)
            .order_by("last_name", "first_name")
        )

    def get_context_data(self, **kwargs):  # pylint: disable=arguments-differ
        # rsvp_yes = RSVPModel.objects.filter(meeting=self.meeting).exclude(response="N").count()
        rsvp_yes = self.get_queryset().count()
        context = {"meeting": self.meeting, "guests": (rsvp_yes)}
        context.update(super().get_context_data(**kwargs))
        return context


class RSVPlistCSVBase(RSVPlist):
    def _lookup_rsvps(self, rsvp):
        if self.private:
            yield [
                "User Id",
                "Username",
                "Last Name",
                "First Name",
                "Email",
                "Added",
            ]
        else:
            yield [
                "Last Name",
                "First Name",
                "Added",
            ]

        for item in rsvp:
            if self.private:
                row = [
                    item.user.id if item.user else "",
                    item.user.username if item.user else "",
                    item.last_name,
                    item.first_name,
                    item.email,
                    item.created,
                ]
            else:
                row = [
                    item.last_name,
                    item.first_name,
                    item.created,
                ]

            yield row

    def render_to_response(self, context, **response_kwargs):
        response = HttpResponse(content_type="text/csv")
        file_name = slugify(f"chipy-export-{self.meeting.id}--{self.meeting.when}")
        response["Content-Disposition"] = f'attachment; filename="{file_name}.csv"'

        writer = csv.writer(response, quoting=csv.QUOTE_ALL)
        for row in self._lookup_rsvps(context["attendees"]):
            writer.writerow(row)

        return response


class RSVPlistPrivate(RSVPlistCSVBase):
    @method_decorator(staff_member_required)
    def dispatch(self, *args, **kwargs):  # pylint: disable=arguments-differ
        return super().dispatch(*args, **kwargs)

    private = True


class RSVPlistHost(RSVPlistCSVBase):
    private = False


class MeetingListAPIView(ListAPIView):
    permission_classes = (IsAPIUser,)

    queryset = Meeting.objects.all()
    serializer_class = MeetingSerializer


class MeetingMeetupSync(APIView):
    permission_classes = (IsAdminUser,)

    def post(self, request, meeting_id):
        meeting = get_object_or_404(Meeting, pk=meeting_id)
        meetup_meeting_sync(settings.MEETUP_API_KEY, meeting.meetup_id)
        return Response()


class UpcomingEvents(TemplateView):
    template_name = "meetings/upcoming_events.html"

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        upcoming_events = Meeting.objects.future_published()[:5]

        all_past_events = Meeting.objects.past_published()

        if upcoming_events.count() > 1:
            past_events = all_past_events[:1]
        else:
            # Assume you have past events [event1, event2, event3].
            # When you order by "-when", it will give you the result [event3, event2, event1].
            # Then you take a slice of two objects, which gives you [event3, event2].
            # This is what you want because you want the 2 most recent events that's occurred.

            # Finally, you must reverse this result order so that it becomes [event2, event3].

            # This is because assume you have upcoming event [event4].
            # When you merge past_events and upcoming_events
            # together, they have to be chronological.
            # So [event2, event3] + [event4] --> [event2, event3, event4]

            past_events = all_past_events[:2]
            past_events = list(reversed(past_events))

        events = []
        # append both past_events and current_events together

        node_orientation = "left"
        for past_event in past_events:
            events.append(
                {
                    "meeting": past_event,
                    "time_status": "inactive",
                    "node_orientation": node_orientation,
                }
            )
            if node_orientation == "left":
                node_orientation = "right"
            else:
                node_orientation = "left"

        for upcoming_event in upcoming_events:
            events.append(
                {
                    "meeting": upcoming_event,
                    "time_status": "active",
                    "node_orientation": node_orientation,
                }
            )
            if node_orientation == "left":
                node_orientation = "right"
            else:
                node_orientation = "left"

        data["events"] = events
        return data
