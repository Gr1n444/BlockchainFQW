from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from users.forms import UserCreationForm
from django.contrib import messages
from main.views import *

class Register(View):
    
    template_name = 'registration.html'

    def get(self, request):
        context = {
            'form': UserCreationForm()
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = UserCreationForm(request.POST)

        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            
            user = authenticate(username=username, password=password)
            if user:
                messages.success(request, 'Success')
                login(request, user)
                return redirect('index')
            else:
                messages.error(request, 'error')
            
        
        context = {
            'form': form
        }
        return render(request, self.template_name, context)