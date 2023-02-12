from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.models import User
from django.contrib import auth
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required

from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode,urlsafe_base64_decode
from django.core.mail import EmailMessage
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_text

from .tokens import account_activation_token
from cp2_don.don_settings import MYSQL_CONN
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.sql import text, intersect

import pandas as pd
import numpy as np
import json

from don_home.models import Ably_token, Cafe24, AblyProductInfo, AblySalesInfo
from don_home.serializers import AblySerializer, Cafe24Serializer, AblyProductSerializer, AblySalseSerializer
from don_home.apis.ably import AblyDataInfo
from don_home.apis.cafe24 import cafe24_df
from don_home.Dashboard.chart_year import Chart_pre_year, Product_total_year, Product_re_year, total_order_year, total_sales_year, detail_order_year
from don_home.Dashboard.chart_month import Chart_pre_month, Product_total_month, Product_re_month, total_order_month, total_sales_month, detail_order_month

from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from rest_framework.parsers import JSONParser



# Create your views here.
def index(request):
    username = request.session.get('user')
    if username:
        log = User.objects.get(pk=username)
    else:
        log = '로그인이 필요합니다.'
    return render(request, 'index.html', {'login' : log})

@csrf_exempt
def signup(request):
    if request.method == 'POST':
        if request.POST['password1'] == request.POST['password2']:
            user = User.objects.create_user(
                username=request.POST['username'], 
                password=request.POST['password1'], 
                first_name = request.POST['fullname'],
                email=request.POST['email'])
            user.is_active = False 
            user.save()
            current_site = get_current_site(request) 
            message = render_to_string('account_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': account_activation_token.make_token(user),
            })
            mail_title = "계정 활성화 확인 이메일"
            mail_to = request.POST["email"]
            email = EmailMessage(mail_title, message, to=[mail_to])
            email.send()
            return HttpResponse(
                '<div style="font-size: 40px; width: 100%; height:100%; display:flex; text-align:center; '
                'justify-content: center; align-items: center;">'
                '입력하신 이메일<span>로 인증 링크가 전송되었습니다.</span>'
                '</div>'
            )

    return render(request, 'signup.html')

@csrf_exempt
def login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, request.POST)
        msg = '아이디 또는 패스워드가 일치하지 않습니다.'
        if form.is_valid():
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password')
            user = auth.authenticate(username=username, password=raw_password)
            if user is not None:
                msg = '로그인 성공'
                auth.login(request, user)
                return redirect('app:index')
        return render(request, "login.html", {"form": form, "msg" : msg})
    else:
        form = AuthenticationForm()
        return render(request, 'login.html', {'form' : form})

def logout(request):
    auth.logout(request)
    return redirect('app:index')


def activate(request, uid64, token):
    try:
        uid = force_text(urlsafe_base64_decode(uid64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and account_activation_token.check_token(user, token):
        user.is_active = True
        user.save()
        auth.login(request, user)
        return redirect('app:index')
    else:
        return render(request, 'index.hmlt', {'error' : '계정 활성화 오류'})

def checkeusername(request):
    try:
        user = User.objects.get(username=request.GET['username'])
    except Exception as e:
        user = None
    result = {
        'result':'success',
        # 'data' : model_to_dict(user)  # console에서 확인
        'data' : "not exist" if user is None else "exist"
    }
    return JsonResponse(result)

# ABLY
@login_required
def ably(request):
    if request.method == 'POST':
        ably_user = Ably_token(
            ably_id=request.POST['ablyid'], 
            ably_pw=request.POST['ablypw'],
            user_id = request.user.id)
        ably_user.save()
        return render(request, 'user/ably_success.html')
    elif request.method == 'GET':
        ably_dataIn = Ably_token.objects.select_related('user').filter(user_id=request.user.id)
        return render(request, 'user/ably.html', {'ably_dataIn' : ably_dataIn})
    

def get_ably_data(reqeust):
    if reqeust.method == 'GET':
        try:
            ably_data = AblySalesInfo.objects.distinct()
        except:
            ably_data = AblySalesInfo.objects.all()
        return JsonResponse(ably_data)

def delete_ably_data(request):
    Ably_token.objects.all().delete()
    return redirect('app:ably')

@login_required
def usertoken(request):
    if request.method == 'GET':
        data = Ably_token.objects.select_related('user').filter(user_id=request.user.id)
        if AblySalesInfo.objects.all():
            results = AblySalesInfo.objects.raw('SELECT * FROM don_home_ablysalesinfo GROUP BY productOrderNumber')

            return render(request, 'user/token_info.html', {'data_list' : data,
                                                            'ably_data' : results})
    elif request.method == 'POST':
        data2 = Ably_token.objects.select_related('user').filter(user_id=request.user.id).values('ably_id', 'ably_pw')
        ably_id = data2[0]['ably_id']
        ably_pw = data2[0]['ably_pw']
        df, df_pro = AblyDataInfo(ably_id, ably_pw)
        for i in range(len(df['paymentDate'])):
            ably_sales = AblySalesInfo (
                paymentDate = df['paymentDate'][i],
                productOrderNumber = df['productOrderNumber'][i],
                orderNumber = df['orderNumber'][i],
                productName = df['productName'][i],
                options = df['options'][i],
                total = df['total'][i],
                orderName = df['orderName'][i],
                phoneNumber = df['phoneNumber'][i],
                orderStatus = df['orderStatus'][i],
                user_id = request.user.id)
            ably_sales.save()
        for i in range(len(df_pro['productNumber'])):
            ably_product = AblyProductInfo (
                productNumber = df_pro['productNumber'][i],
                productName = df_pro['productName'][i],
                price = df_pro['price'][i],
                discountPeriod = df_pro['discountPeriod'][i],
                discountPrice = df_pro['discountPrice'][i],
                registrationDate = df_pro['registrationDate'][i],
                statusDisplay = df_pro['statusDisplay'][i],
                stock = df_pro['stock'][i],
                totalReview = df_pro['totalReview'][i],
                parcel = df_pro['parcel'][i],
                returnShippingCost = df_pro['returnShippingCost'][i],
                extraShippingCost = df_pro['extraShippingCost'][i],
                user_id = request.user.id)
            ably_product.save()
        return render(request, 'user/token_info.html', {'df' : df, 
                                                        'df_pro' : df_pro,})
    return render(request, 'user/token_info.html')


# CAFE24
@login_required
def cafe24(request):
    if request.method == 'POST':
        cafe24_user = Cafe24(
            cafe24_id = request.POST['cafe24id'],
            cafe24_pw = request.POST['cafe24pw'],
            cafe24_clientid = request.POST['cafe24_clientid'],
            cafe24_client_secret = request.POST['cafe24_client_secret'],
            cafe24_mallid = request.POST['cafe24_mallid'],
            cafe24_encode_csrf_token = request.POST['cafe24_encode_csrf_token'],
            cafe24_redirect_uri = request.POST['cafe24_redirect_uri'],
            service_key = request.POST['cafe24_service_key'],
            user_id = request.user.id)
        cafe24_user.save()
        return render(request, 'user/cafe24_success.html')
    elif request.method == 'GET':
        cafe24_info = Cafe24.objects.select_related('user').filter(user_id=request.user.id)
        return render(request, 'user/cafe24.html', {'cafe24_info': cafe24_info})

def delete_cafe24_data(request):
    Cafe24.objects.all().delete()
    return redirect('app:cafe24')

# DRF
@api_view(['GET', 'POST'])
def ablyproduct_api(request):
    if request.method == 'GET':
        ably_info = Ably_token.objects.select_related('user').values('ably_id', 'ably_pw')
        ably_id = ably_info[0]['ably_id']
        ably_pw = ably_info[0]['ably_pw']

        df, df_pro = AblyDataInfo(ably_id, ably_pw)
        for i in range(len(df_pro['productNumber'])):
            ably_product = AblyProductInfo (
                productNumber = df_pro['productNumber'][i],
                productName = df_pro['productName'][i],
                price = df_pro['price'][i],
                discountPeriod = df_pro['discountPeriod'][i],
                discountPrice = df_pro['discountPrice'][i],
                registrationDate = df_pro['registrationDate'][i],
                statusDisplay = df_pro['statusDisplay'][i],
                stock = df_pro['stock'][i],
                totalReview = df_pro['totalReview'][i],
                parcel = df_pro['parcel'][i],
                returnShippingCost = df_pro['returnShippingCost'][i],
                extraShippingCost = df_pro['extraShippingCost'][i],
                user_id = request.user.id)
            ably_product.save()
        
        articles = AblyProductInfo.objects.raw('SELECT * FROM don_home_ablyproductinfo GROUP BY productNumber')
        serializer = AblyProductSerializer(articles, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = AblyProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'POST'])
def ablysales_api(request):
    if request.method == 'GET':
        ably_info = Ably_token.objects.select_related('user').values('ably_id', 'ably_pw')
        ably_id = ably_info[0]['ably_id']
        ably_pw = ably_info[0]['ably_pw']

        df, df_pro = AblyDataInfo(ably_id, ably_pw)
        for i in range(len(df['paymentDate'])):
            ably_sales = AblySalesInfo (
                paymentDate = df['paymentDate'][i],
                productOrderNumber = df['productOrderNumber'][i],
                orderNumber = df['orderNumber'][i],
                productName = df['productName'][i],
                options = df['options'][i],
                total = df['total'][i],
                orderName = df['orderName'][i],
                phoneNumber = df['phoneNumber'][i],
                orderStatus = df['orderStatus'][i],
                user_id = request.user.id)
            ably_sales.save()

        articles = AblySalesInfo.objects.raw('SELECT * FROM don_home_ablysalesinfo GROUP BY productOrderNumber')
        serializer = AblySalseSerializer(articles, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = AblySalseSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
def cafe24all_api(request):
    if request.method == 'GET':
        cafe24_info = Cafe24.objects.select_related('user').values('cafe24_id','cafe24_pw','cafe24_clientid',
                                                                   'cafe24_client_secret','cafe24_mallid',
                                                                   'cafe24_encode_csrf_token','cafe24_redirect_uri',)
        cafe24_id = cafe24_info[0]['cafe24_id']
        cafe24_pw = cafe24_info[0]['cafe24_pw']
        clientid = cafe24_info[0]['cafe24_clientid']
        client_secret = cafe24_info[0]['cafe24_client_secret']
        mallid = cafe24_info[0]['cafe24_mallid']
        encode_csrf_token = cafe24_info[0]['cafe24_encode_csrf_token']
        redirect_uri = cafe24_info[0]['cafe24_redirect_uri']
        
        category_df, product_df, order_df, coupon_df = cafe24_df(cafe24_id, cafe24_pw, clientid, client_secret, mallid, encode_csrf_token, redirect_uri)

        engine = create_engine(MYSQL_CONN)

        tableName='don_home_cafe24category'
        category_df.to_sql(name=tableName, con=engine, index=False, if_exists='replace')

        tableName1='don_home_cafe24product'
        product_df.to_sql(name=tableName1, con=engine, index=False, if_exists='replace')

        tableName2='don_home_cafe24order'
        order_df.to_sql(name=tableName2, con=engine, index=False, if_exists='replace')

        tableName3='don_home_cafe24coupon'
        coupon_df.to_sql(name=tableName3, con=engine, index=False, if_exists='replace')

        return Response(cafe24_info)


def dashboard(request):
    engine = create_engine(MYSQL_CONN)
    Session = scoped_session(sessionmaker(bind=engine))
    s = Session()
    conn = engine.raw_connection()
    select_box = request.GET.get('order_date')

    to_d, ab_d, cf_d, na_d = detail_order_year()
    # 총 판매가
    result_t, ab_sales, cf_sales, na_sales = total_sales_year()
    # 총 주문 건수
    to_cou_order, ab_cou_order, cf_cou_order, na_cou_order = total_order_year()
    # 매출 현황 Bar 그래프
    to_mon, to_data_t, ab_data, ab_mon, cf_data, cf_mon, na_data, na_mon = Chart_pre_year()
    # 제품 별 판매현황
    tpn, tpt, apn, apt, cpn, cpt, npn, npt = Product_total_year()
    # 총 반품 건수
    nare, cfre, abre, tore = Product_re_year()

    if select_box == 'odyear':
        # 주문 내역 상세
        to_d, ab_d, cf_d, na_d = detail_order_year()
        # 총 판매가
        result_t, ab_sales, cf_sales, na_sales = total_sales_year()
        # 총 주문 건수
        to_cou_order, ab_cou_order, cf_cou_order, na_cou_order = total_order_year()
        # 매출 현황 Bar 그래프
        to_mon, to_data_t, ab_data, ab_mon, cf_data, cf_mon, na_data, na_mon = Chart_pre_year()
        # 제품 별 판매현황
        tpn, tpt, apn, apt, cpn, cpt, npn, npt = Product_total_year()
        # 총 반품 건수
        nare, cfre, abre, tore = Product_re_year()

        context = {'td':to_d,'ab':ab_d,'cf':cf_d,'na':na_d,
                    'total':result_t,'ably_plat':ab_sales,'cafe_plat':cf_sales,'naver_plat':na_sales,
                    'total_order':to_cou_order,'ably_order':ab_cou_order,'cafe_order':cf_cou_order,'naver_order':na_cou_order,
                    'total_re':tore,'ably_re':abre,'cafe_re':cfre,'naver_re':nare,
                    'to_mon':to_mon,'to_data':to_data_t,'ab_mon':ab_mon,'ab_data':ab_data,'cf_mon':cf_mon,'cf_data':cf_data,'na_mon':na_mon,'na_data':na_data,
                    'tpn':tpn, 'tpt':tpt, 'apn':apn, 'apt':apt, 'cpn':cpn, 'cpt':cpt, 'npn':npn, 'npt':npt
                    }
        return render(request, 'dashboard.html', context = context)

    elif select_box == 'odmonth':
        # 주문 내역 상세
        to_d, ab_d, cf_d, na_d = detail_order_month()
        # 총 판매가
        result_t, ab_sales, cf_sales, na_sales = total_sales_month()
        # 총 주문 건수
        to_cou_order, ab_cou_order, cf_cou_order, na_cou_order = total_order_month()
        # 매출 현황 Bar 그래프
        to_mon, to_data_t, ab_data, ab_mon, cf_data, cf_mon, na_data, na_mon = Chart_pre_month()
        # 제품 별 판매현황
        tpn, tpt, apn, apt, cpn, cpt, npn, npt = Product_total_month()
        # 총 반품 건수
        mnare, mcfre, mabre, mtore = Product_re_month()

        context = {'td':to_d,'ab':ab_d,'cf':cf_d,'na':na_d,
                    'total':result_t,'ably_plat':ab_sales,'cafe_plat':cf_sales,'naver_plat':na_sales,
                    'total_order':to_cou_order,'ably_order':ab_cou_order,'cafe_order':cf_cou_order,'naver_order':na_cou_order,
                    'total_re':mtore,'ably_re':mabre,'cafe_re':mcfre,'naver_re':mnare,
                    'to_mon':to_mon,'to_data':to_data_t,'ab_mon':ab_mon,'ab_data':ab_data,'cf_mon':cf_mon,'cf_data':cf_data,'na_mon':na_mon,'na_data':na_data,
                    'tpn':tpn, 'tpt':tpt, 'apn':apn, 'apt':apt, 'cpn':cpn, 'cpt':cpt, 'npn':npn, 'npt':npt
                    }
        return render(request, 'dashboard.html', context = context)

        
    elif select_box == 'odweek':
        pass
    

    conn.close()
    engine.dispose()

    context = {'td':to_d,'ab':ab_d,'cf':cf_d,'na':na_d,
                    'total':result_t,'ably_plat':ab_sales,'cafe_plat':cf_sales,'naver_plat':na_sales,
                    'total_order':to_cou_order,'ably_order':ab_cou_order,'cafe_order':cf_cou_order,'naver_order':na_cou_order,
                    'total_re':tore,'ably_re':abre,'cafe_re':cfre,'naver_re':nare,
                    'to_mon':to_mon,'to_data':to_data_t,'ab_mon':ab_mon,'ab_data':ab_data,'cf_mon':cf_mon,'cf_data':cf_data,'na_mon':na_mon,'na_data':na_data,
                    'tpn':tpn, 'tpt':tpt, 'apn':apn, 'apt':apt, 'cpn':cpn, 'cpt':cpt, 'npn':npn, 'npt':npt
                    }

    return render(request, 'dashboard.html', context=context)