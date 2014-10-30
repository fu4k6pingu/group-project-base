import json
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.core.validators import validate_email
from django.http import HttpResponse
from django.shortcuts import render, redirect
from slides.forms import UpdateUserImageForm
from django.views.decorators.csrf import csrf_exempt
from slides.forms import ProfileForm
from slides.models import Profile, Slide, Action, Question


@login_required
def account(request):
    if request.method == 'POST':
        imageform = UpdateUserImageForm(request.POST, request.FILES, instance=request.user)
        if imageform.is_valid():
            imageform.save()
    else:
        imageform = UpdateUserImageForm()
    return render(request, 'account.html', {
        'imageform': imageform,
    })


@csrf_exempt
def edit_name(request):
    status = None
    if request.method == 'POST':
        data = json.loads(request.body)
        if data:
            request.user.real_name = data
            request.user.save()
            status = "success"
    response = status
    return HttpResponse(json.dumps(response),
                        content_type='application/json')


@csrf_exempt
def edit_email(request):
    status = None
    if request.method == 'POST':
        data = json.loads(request.body)
        try:
            validate_email(data)
            request.user.email = data
            request.user.save()
            status = "success"
        except ValidationError:
            pass
    response = status
    return HttpResponse(json.dumps(response),
                        content_type='application/json')


@csrf_exempt
def edit_password(request):
    status = None
    if request.method == 'POST':
        data = json.loads(request.body)
        if not data[0] == data[1]:                    #check passwords are correctly repeated
            status = "mismatch"
        elif data[0]:
            user = request.user
            user.set_password(data[1])
            user.save()
            status = "success"
            update_session_auth_hash(request, user)
    response = status
    return HttpResponse(json.dumps(response),
                        content_type='application/json')


@csrf_exempt
def edit_photo(request):
    status = None
    if request.method == 'POST':
        data = json.loads(request.body)
        request.user.photo = data
        request.user.save()
        status = "success"
    response = status
    return HttpResponse(json.dumps(response),
                        content_type='application/json')


def register(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES)
        if form.is_valid():
            username = request.POST["username"]
            password = request.POST["password1"]
            form.save()
            user = authenticate(username=username, password=password)
            if user:
                if user.is_active:
                    login(request, user)
                    return redirect("slides_home")
    else:
        form = ProfileForm()

    return render(request, "registration/register.html", {
        'form': form,
    })


@csrf_exempt
def new_action(request, action):
    if request.method == 'POST':
        data = json.loads(request.body)
        student = Profile.objects.get(username=request.user.username)
        week = int(data['week'])
        am_pm = int(data['am_pm'])
        slide_number = int(data['slide_number'])
        new_slides = Slide.objects.filter(week=week, day=data["day"])
        print new_slides
        day = data['day']
        our_url = "week"+str(week)+"/"+day+"/#/"+str(slide_number)
        print our_url
        current_slide = Slide.objects.get(url=our_url)
        print current_slide
        # HELP
        if int(action) == 1:
            try:
                done_action = Action.objects.get(done=True, profile=student, slide=current_slide)
                done_action.done = False
                done_action.need_help = True
                done_action.save()
            except ObjectDoesNotExist:
                Action.objects.get_or_create(need_help=True, profile=student, slide=current_slide)
            # Action.objects.get_or_create(need_help=True, profile=student, slide=current_slide)
        # DONE
        elif int(action) == 2:
            try:
                help_action = Action.objects.get(need_help=True, profile=student, slide=current_slide)
                help_action.done = True
                help_action.need_help = False
                help_action.save()
            except ObjectDoesNotExist:
                Action.objects.get_or_create(done=True, profile=student, slide=current_slide)
        # QUESTION
        elif int(action) == 3:
            Question.objects.get_or_create(profile=student, slide=current_slide, body=data['text'])

    return HttpResponse(content_type='application/json')


def teacher(request, week, day, am_pm):
    deck = Slide.objects.filter(week=int(week), day=str(day))
    deck.filter(am_pm=am_pm)
    return_list = []
    for slide in deck:
        return_list.append({
            'slide': slide,
            'done': Action.objects.filter(slide=slide, done=True).count(),
            'need_help': Action.objects.filter(slide=slide, need_help=True).count(),
            'questions': Question.objects.filter(slide=slide).count(),
        })

    data = {
        "deck": deck,
        'return_list': return_list
    }
    return render(request, "teacher.html", data)

def teacher_help(request):
    students = Profile.objects.all()
    help = Action.objects.filter(need_help=True, done=False)
    data = {'help': help, 'students': students}
    return render(request, 'teacher/help.html', data)


def teacher_done(request, slide_url):
    student = Profile.objects.filter(is_student=True)
    actions = Action.objects.filter(slide=Slide.objects.get(url=slide_url))
    done = actions.filter(done=True)
    exclude_pk = done.values_list('profile__pk', flat=True)
    not_done_students = student.exclude(pk__in=exclude_pk)

    slide = Slide.objects.filter(url=slide_url)

    data = {'done': done, 'not_done': not_done_students}
    return render(request, 'teacher/done.html', data)


def teacher_question(request):
    students = Profile.objects.all()
    question = Question.objects.all()
    data = {'question': question, 'students': students}
    return render(request, 'teacher/questions.html', data)


@csrf_exempt
def change_action(request, action):
    if request.method == 'POST':
        data = json.loads(request.body)
