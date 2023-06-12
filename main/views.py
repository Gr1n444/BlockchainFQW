import os
import hashlib
import json
import requests
import atexit
import imagehash
import PIL.ExifTags
from uuid import uuid4
from io import BytesIO
from datetime import datetime
from urllib.parse import urlparse
from imagededup.methods import PHash
from PIL import Image, TiffImagePlugin, ImageDraw, ImageFont
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required


class Blockchain(object):
    def __init__(self):

        # Цепь блокчейна
        self.chain = []
        # Переменные для работы с созданием блоков
        self.current_data = []
        self.current_owner = None
        # Используемые в сети ноды
        self.nodes = set()
        # Создание генезис-блока (начальный блок в цепи)
        self.new_block(previous_hash=1, proof=100)
        #self.load_data_from_backup(filename='backup.json')

        # Хранение блоков, принадлежащих определенному пользователю, выдаваемых по запросу
        self.tmp_user_blocks = []
        

    @atexit.register
    def backup_blockchain(self):
        with open('backup.json', 'w') as file:
            json.dump(self.chain, file, ensure_ascii=False)

    def load_data_from_backup(self, filename):
        with open(filename, 'r') as f:
            self.chain = json.load(f)

    def new_block(self, proof, previous_hash=None):
        """
        Создание нового блока в блокчейне

        :param proof: <int> Доказательства проведенной работы
        :param previous_hash: (Опционально) хеш предыдущего блока
        :return: <dict> Новый блок
        """

        block = {
            'index': len(self.chain) + 1,
            'time': str(datetime.now()),
            'owner': self.current_owner,
            'data': self.current_data,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # Перезагрузка текущего списка транзакций
        self.current_data = []
        self.current_owner = None

        self.chain.append(block)
        return block

    def new_data(self, owner, description, watermark, hash_image, node_id, data, file_url, name):
        """
        Направляет информацию о новом токене в следующий блок

        :param owner: <str> Имя владельца
        :param description: <str> Описание загружаемого файла (например, логотип или изображение)
        :param watermark: <int> Секретное выражение для подтверждения подлинности
        :return: <int> Индекс блока, который будет хранить эту информацию
        """
        self.current_owner = owner

        self.current_data.append({
            'description': description,
            'text_for_watermark': watermark,
            'node': node_id,
            'hash_image': hash_image,
            'exif': data,
            'url': file_url,
            'name': name
        })

        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        """
        Создает хэш SHA-256 блока

        :param block: <dict> Блок
        :return: <str>
        """

        # Нужно убедиться, что список будет упорядочен, иначе значения хэш-функций будут непоследовательны
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        """
        Простая проверка алгоритма:
         - Поиска числа p`, так как hash(pp`) содержит 4 заглавных нуля, где p - предыдущий
         - p является предыдущим доказательством, а p` - новым

        :param last_proof: <int>
        :return: <int>
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Подтверждение доказательства: Содержит ли hash(last_proof, proof) 4 заглавных нуля?

        :param last_proof: <int> Предыдущее доказательство
        :param proof: <int> Текущее доказательство
        :return: <bool> True, если правильно, False, если нет.
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def register_node(self, address):
        """
        Вносим новый узел в список узлов

        :param address: <str> адрес узла , другими словами: 'http://192.168.0.5:5000'
        :return: None
        """

        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        """
        Проверяем, является ли внесенный в блок хеш корректным

        :param chain: <list> blockchain
        :return: <bool> True если она действительна, False, если нет
        """

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f'{last_block}')
            print(f'{block}')
            print("\n-----------\n")
            # Проверьте правильность хеша блока
            if block['previous_hash'] != self.hash(last_block):
                return False

            # Проверяем, является ли подтверждение работы корректным
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        Это наш алгоритм Консенсуса, он разрешает конфликты,
        заменяя нашу цепь на самую длинную в цепи

        :return: <bool> True, если бы наша цепь была заменена, False, если нет.
        """

        neighbours = self.nodes
        new_chain = None

        # Ищем только цепи, длиннее нашей
        max_length = len(self.chain)

        # Захватываем и проверяем все цепи из всех узлов сети
        for node in neighbours:
            response = requests.get(f'http://{node}/get_chain')

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # Проверяем, является ли длина самой длинной, а цепь - валидной
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Заменяем нашу цепь, если найдем другую валидную и более длинную
        if new_chain:
            self.chain = new_chain
            return True

        return False

    def show_user_blocks(self, chain, user):
        print('chain:', type(blockchain.chain))
        print('current_data:',type(blockchain.current_data))
        print('nodes', type(blockchain.nodes))
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            if block['owner'] == user:
                self.tmp_user_blocks.append(block)

            current_index += 1

    def search_duplicate_images(self, chain, current_hash):

        current_index = 1
        
        for block in chain:
            if block['index'] == 1:
                continue
            
            if current_hash - imagehash.hex_to_hash(block['data'][0]['hash_image']) <= 10:
                self.tmp_user_blocks.append(block)
                current_index += 1
                return True
            
            current_index += 1

        return False

    def watermark(self, converted_image, watermark):
        drawing = ImageDraw.Draw(converted_image)

        width, height = converted_image.size
        font = ImageFont.truetype('arial.ttf', int(height * 0.03))
        color = (85, 113, 96, 50)

        tmp = [0.01, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        for i in range(10):
            pos = (width * tmp[i], height * tmp[i])
            drawing.text(pos, watermark, fill=color, font=font)

        return converted_image
    
    def metadata(self, converted_image):
        dct = {}
        for k, v in converted_image.getexif().items():
            if k in PIL.ExifTags.TAGS:
                if isinstance(v, TiffImagePlugin.IFDRational):
                    v = float(v)
                elif isinstance(v, tuple):
                    v = tuple(float(t) if isinstance(t, TiffImagePlugin.IFDRational) else t for t in v)
                elif isinstance(v, bytes):
                    v = v.decode(errors="replace")
                dct[PIL.ExifTags.TAGS[k]] = v 
        return dct       


blockchain = Blockchain()
node_address = str(uuid4()).replace('-', '')


@login_required
@csrf_exempt
def new_data(request):
    if request.method == 'POST':
        owner = request.user.username
        description = request.POST.get('description')
        watermark = request.POST['watermark']
        file = request.FILES.get('file')
        user_path = f'media/{owner}'
        archive_path = 'media/archive'
        filename = file.name
        if not owner or not description or not watermark or not file:
            return JsonResponse({'error': 'All fields are required!'}, status=400)

        buffer = BytesIO()
        for chunk in file.chunks():
            buffer.write(chunk)

        image = Image.open(buffer)
        converted_image = image.convert('RGB')

        hash_image = imagehash.phash(converted_image)
        hash_as_str = str(hash_image)
        check = blockchain.search_duplicate_images(blockchain.chain, hash_image)

        if check:
            response = {
                'message': 'similar images found in the blockchain',
                'founded_images': blockchain.tmp_user_blocks
            }
        else:
            converted_image = blockchain.watermark(converted_image, watermark)
            converted_image.save(f'C:/BlockchainFQW/{archive_path}/{filename}')
            fs = FileSystemStorage(location=user_path)
            fs.save(filename, file)
            absolute_url = request.build_absolute_uri(f'/{archive_path}/') + filename

            dct = blockchain.metadata(converted_image)
            data = json.dumps(dct)

            blockchain.resolve_conflicts()
            index = blockchain.new_data(owner, description, watermark,
                                        hash_as_str, node_address, data,
                                        absolute_url, filename)

            response = {
                'message': f'Data will be added to Block {index}',
            }
        return JsonResponse(response, status=200, json_dumps_params={'indent': 4, "ensure_ascii": False})


@login_required
def mine_block(request):
    if request.method == 'GET':
        last_block = blockchain.last_block
        last_proof = last_block['proof']
        proof = blockchain.proof_of_work(last_proof)

        previous_hash = blockchain.hash(last_block)
        block = blockchain.new_block(proof, previous_hash)


    response = {
        'message': 'New Block added to Blockchain!',
        'index': block['index'],
        'owner': block['owner'],
        'data': block['data'],
        'proof': block['proof'],
        'previous_block_hash': block['previous_hash'],
        
    }
    blockchain.backup_blockchain()
    return JsonResponse(response, json_dumps_params={'indent': 4, "ensure_ascii": False})


# Вывод полной цепи блокчейна по запросу
def get_full_chain(request):
    if request.method == 'GET':
        response = {
            'chain': blockchain.chain,
            'length': len(blockchain.chain)
        }
    return JsonResponse(response, json_dumps_params={'indent': 4, "ensure_ascii": False})


def valid_blockchain(request):
    if request.method == 'GET':
        blockchain_valid = blockchain.valid_chain(blockchain.chain)
        if blockchain_valid:
            response = {
                'Message': 'Blockchain is valid, all blocks are True',
                'Actual chain': blockchain.chain
            }
        else:
            response = {
                'Message': 'Blockchain is not valid, check blocks!'}
        return JsonResponse(response, json_dumps_params={'indent': 4, "ensure_ascii": False})


@csrf_exempt
def connect_new_node(request):
    if request.method == 'POST':
        received_json = json.loads(request.body)
        nodes = received_json.get('nodes')
        if nodes is None:
            return "No nodes founded, try again!", HttpResponse(status=400)
        for node in nodes:
            blockchain.register_node(node)
        response = {
            'message': 'New nodes have been added in list',
            'total_nodes': list(blockchain.nodes)
        }
        return JsonResponse(response, json_dumps_params={'indent': 4, "ensure_ascii": False})


def consensus(request):
    if request.method == 'GET':
        replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Chain was replaced',
            'chain': blockchain.chain
        }
    else:
        response = {
            'message': 'All good. The chain is the largest one',
            'actual_chain': blockchain.chain
        }
    return JsonResponse(response, json_dumps_params={'indent': 4, "ensure_ascii": False})


def users_blocks(request):
    if request.method == 'GET':
        user = request.user.username

        blockchain.show_user_blocks(blockchain.chain, user)
        if blockchain.tmp_user_blocks == []:
            response = {
                'message': f'No blocks for {user}',
            }
        else:
            response = {
                'message': f'Blocks for {user}',
                'actual_blocks': blockchain.tmp_user_blocks
            }
            blockchain.tmp_user_blocks = []
        return JsonResponse(response, json_dumps_params={'indent': 4, "ensure_ascii": False})


def check_images(request):
    if request.method == 'POST':
        file = request.FILES.get('file')
        if not file:
            filename = request.POST['filename']
        

        phasher = PHash()
        encodings = phasher.encode_images(image_dir='C:/BlockchainFQW/media/archive')
        duplicates = phasher.find_duplicates(encoding_map=encodings)

        response = {
            'message': 'success',
            f'duplicates for {filename}': duplicates[filename]
        }

        return JsonResponse(response, json_dumps_params={'indent': 4, "ensure_ascii": False})
    
from django.http import HttpResponse
from django.shortcuts import render
from django.conf import settings

def show_images(request, ):
    if request.method == 'GET':
        username = request.user.username
        # Получаем путь к директории пользователя
        user_dir = os.path.join(settings.MEDIA_ROOT, username)
        
        # Получаем список файлов из директории пользователя
        files = os.listdir(user_dir)
        
        # Фильтруем список файлов, оставляя только изображения
        images = filter(lambda file: file.endswith(('.png', '.jpg', '.jpeg', '.gif')), files)
        
        # Создаем список словарей, содержащих путь и имя каждого изображения
        images_data = [{'path': os.path.join(settings.MEDIA_URL, username, image), 'name': image} for image in images]
        
        # Отображаем список изображений на HTML странице с помощью шаблона Django
        return render(request, 'images.html', {'images': images_data})