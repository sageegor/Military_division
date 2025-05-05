from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Division

MINIO_URL = "http://127.0.0.1:9000/buckets/militarydivision"
# Create your views here.

cart = {}


def GetOrders(request):
    divisions = Division.objects.filter(is_active=True)  # Берем только активные подразделения
    query = request.GET.get('q', '')

    if query:
        divisions = divisions.filter(name__icontains=query)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'divisions': list(divisions.values('id', 'name', 'description', 'image_url'))
        })

    return render(request, 'orders.html', {'divisions': divisions})
def GetOrder(request, id):
    division = get_object_or_404(Division, id=id)
    return render(request, 'order.html', {'division': division})
def cart_detail(request):
    return render(request, 'cart_detail.html', {'cart' :cart})

def add_to_cart(request, id):
    global cart
    if request.method == "POST":
        division = get_object_or_404(Division, id=id)
        cart[id] = {
            'id': division.id,
            'name': division.name,
            'description': division.description,
            'image_url': division.image_url
        }
        return GetOrders(request)


def get_divisions_partial(request):
    divisions = [
        {'id': 1, 'name':'69-я гвардейская мотострелковая дивизия', 'description':'69 - я гвардейская стрелковая дивизия. Сформирована в феврале 1943 года и служила до окончания Великой Отечественной войны. После войны дивизия в 1953 году была преобразована в 70-ю гвардейскую стрелковую дивизию. Повторно реформирована в мае 2024 года.','image_url':'http://127.0.0.1:9000/militarydivision/69%20GMD.jpg'},
        {'id': 2, 'name':'9-я гвардейская артиллерийская бригада', 'description':'Бригада ведёт свою историю от 200-й лёгкой артиллерийской бригады, сформированной 1 октября 1944 года. 4 апреля 1945 года преобразована в 71-ю гвардейскую лёгкую артиллерийскую бригаду. В 1960 году  была переименована в 113-й гвардейский артиллерийский полк. В 1981 году полк был переименован в 387-ю гвардейскую артиллерийскую бригаду. В 1993 году была переименована в 9-ю гвардейскую артиллерийскую бригаду.','image_url':'http://127.0.0.1:9000/militarydivision/9%20GAB.jpg'},
        {'id': 3, 'name':'2-я дивизия ПВО', 'description':'Сформированный в 1986 году 54-й корпус ПВО входил в состав 6-й отдельной армии противовоздушной обороны, а с 1998 года — 6-й армии ВВС и ПВО.  В 2009 году она была реорганизована во 2-ю бригаду противовоздушной обороны, в 2013 году — во 2-ю бригаду противовоздушной и противоракетной обороны, а в 2014 году — во 2-ю дивизию противовоздушной обороны.','image_url':'http://127.0.0.1:9000/militarydivision/2%20d%20PVO.jpg'},
        {'id': 4, 'name':'4-я гвардейская танковая дивизия', 'description':'Предшественником дивизии был 17-й танковый корпус сформированный в 1942 году вскоре после начала немецкого вторжения в Советский Союз. в январе 1943 года был переименован в 4-й гвардейский танковый корпус. В 2009 году дивизия была сокращена до 4-й отдельной гвардейской танковой бригады. В мае 2013 года из танковой бригады была сформирована Кантемировская дивизия.','image_url':'http://127.0.0.1:9000/militarydivision/4%20GTD.jpg'},
        {'id': 5, 'name':'18-я пулеметно-артиллерийская дивизия', 'description':'Впервые она была сформирована как 184-я Краснознамённая стрелковая дивизия. 8 июня 1946 года на базе 184-й стрелковой дивизии и 18-й пулемётно-артиллерийской бригады была создана 18-я пулемётно-артиллерийская дивизия. Он был расформирован в 1949 году. Подразделение было сформировано в середине мая 1978 года в Князе-Волконском, Хабаровский край, без преемственности от предыдущего формирования.','image_url':'http://127.0.0.1:9000/militarydivision/18%20PAD.jpg'},
        {'id': 6, 'name':'22-й армейский корпус','description':'22-й армейский корпус был сформирован 1 декабря 2016 года. В состав корпуса входят подразделения береговых войск Черноморского флота. 126-я бригада береговой обороны была сформирована из состава предыдущего украинского формирования в декабре 2014 года и вошла в состав корпуса. В декабре 2018 года корпус был представлен к наградам за выдающиеся заслуги в боевых действиях.','image_url':'http://127.0.0.1:9000/militarydivision/22%20AK.jpg'}
    ]
    query = request.GET.get('q', '')

    if query:
        divisions = [d for d in divisions if query.lower() in d['name'].lower()]

    return render(request, 'divisions_list.html', {'divisions': divisions})