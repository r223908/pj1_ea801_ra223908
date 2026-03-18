from machine import Pin, ADC, I2C
import neopixel, utime

from libs import ssd1306

# ==========================================
# Configuração dos Botões (A, B e C)
# Pinos conectados ao GND, exigem PULL_UP interno
# ==========================================
botao_a = Pin(5, Pin.IN, Pin.PULL_UP)
botao_b = Pin(6, Pin.IN, Pin.PULL_UP)
botao_c = Pin(10, Pin.IN, Pin.PULL_UP)

# Índices das cores atuais
idx_esq = 2   # Começa no Azul
idx_dir = 0   # Começa no Vermelho
idx_meio = 1  # Começa no Verde
ultimo_tempo_btn = 0

# Função de Callback (Handler) que é chamada pelo "trig" do botão
def trata_interrupcao_botao(pino):
    global idx_esq, idx_dir, idx_meio, ultimo_tempo_btn
    tempo_atual = utime.ticks_ms()
    # "Debounce" de 200ms: evita que interferências ou o ressalto mecânico 
    # da mola do botão acionem a interrupção múltiplas vezes
    if utime.ticks_diff(tempo_atual, ultimo_tempo_btn) > 200:
        if pino == botao_a:
            idx_esq = (idx_esq + 1) % len(PALETA)
        elif pino == botao_b:
            idx_dir = (idx_dir + 1) % len(PALETA)
        elif pino == botao_c:
            idx_meio = (idx_meio + 1) % len(PALETA)
        ultimo_tempo_btn = tempo_atual

# Atribuir as interrupções aos botões na "borda de descida" (quando pressionados)
botao_a.irq(trigger=Pin.IRQ_FALLING, handler=trata_interrupcao_botao)
botao_b.irq(trigger=Pin.IRQ_FALLING, handler=trata_interrupcao_botao)
botao_c.irq(trigger=Pin.IRQ_FALLING, handler=trata_interrupcao_botao)

# ==========================================
# Configuração do Joystick (Analógico KY-023)
# ==========================================
# Eixos X e Y nos conversores analógico-digitais (ADC)
joystick_x = ADC(Pin(27))
joystick_y = ADC(Pin(26))

# Botão do joystick (SW) conectado ao GND, exige PULL_UP
joystick_sw = Pin(22, Pin.IN, Pin.PULL_UP)

# ==========================================
# Variáveis de Controle do Motor Virtual
# ==========================================
CENTRO_JOYSTICK = 32768
ZONA_MORTA = 4000
MAX_LEDS_POR_SEGUNDO = 10.0 # Velocidade máxima virtual (piscas por segundo)

# ==========================================
# Configuração do Display OLED (SSD1306 - 128x64)
# Canal I2C 1, SDA no GPIO2, SCL no GPIO3
# ==========================================
i2c = I2C(1, scl=Pin(3), sda=Pin(2), freq=400000)
display = ssd1306.SSD1306_I2C(128, 64, i2c, addr=0x3C)

# Limpa o display no início para garantir que não haja "lixo" na memória
display.fill(0)
display.show()

# Variáveis para controle não-bloqueante do pisca
ultimo_tempo = utime.ticks_ms()
estado_led_motor = False

# Número de LEDs na sua matriz 5x5
NUM_LEDS = 25
# Inicializar a matriz de NeoPixels no GPIO7
np = neopixel.NeoPixel(Pin(7), NUM_LEDS)
# Definindo a matriz de sLEDs
LED_MATRIX = [
    [24, 23, 22, 21, 20],
    [15, 16, 17, 18, 19],
    [14, 13, 12, 11, 10],
    [5, 6, 7, 8, 9],
    [4, 3, 2, 1, 0]
]
# Com base na sua disposição, a linha do meio é: [14, 13, 12, 11, 10]
LED_EXT_ESQUERDA = 14  # Equivalente a motor girando para um lado
LED_MEIO = 12          # Indicador de Zona Morta (Parado)
LED_EXT_DIREITA = 10   # Equivalente a motor girando para o outro lado
corVermelha = (20, 0, 0)
corAzul = (0, 0, 20)
corVerde = (0, 20, 0)

# Garante que todos os LEDs comecem apagados
for i in range(NUM_LEDS):
    np[i] = (0, 0, 0)
np.write()

def printOled():
    # Lê o estado do botão (como usa pull-up, 0 significa pressionado)
    estado_botao = "Pressionado" if joystick_sw.value() == 0 else "Solto"
    
    # Limpa a tela antes de desenhar o novo quadro
    display.fill(0)
    
    # Adiciona os textos na memória do display (texto, coluna_x, linha_y)
    display.text("BitDogLab V7", 16, 0)
    display.text("-" * 16, 0, 10)
    
    # Envia os dados da memória para a tela efetivamente
    display.show()
    
    # Uma pequena pausa para não sobrecarregar o display e evitar "flicker"
    utime.sleep(0.1)


# ==========================================
# Variáveis de Controle do Motor Virtual
# ==========================================
CENTRO_JOYSTICK = 32768
ZONA_MORTA = 4000
MAX_LEDS_POR_SEGUNDO = 10.0

# ==========================================
# Lógica de Cores e Interrupções (IRQs)
# ==========================================
# Paleta de cores para ir alternando (R, G, B)
PALETA = [
    (50, 0, 0),   # Vermelho
    (0, 50, 0),   # Verde
    (0, 0, 50),   # Azul
    (50, 50, 0),  # Amarelo
    (50, 0, 50),  # Magenta
    (0, 50, 50),  # Ciano
    (50, 50, 50)  # Branco
]


ultimo_tempo_pisca = utime.ticks_ms()
estado_led_motor = False

# Garante que todos os LEDs começam apagados
for i in range(NUM_LEDS):
    np[i] = (0, 0, 0)
np.write()

# ==========================================
# Ciclo Principal (Independente dos Botões)
# ==========================================
while True:
    printOled()

    valor_y = joystick_y.read_u16()
    desvio = valor_y - CENTRO_JOYSTICK

    np[LED_EXT_ESQUERDA] = (0, 0, 0)
    np[LED_MEIO] = (0, 0, 0)
    np[LED_EXT_DIREITA] = (0, 0, 0)

    # 1. Zona Morta
    if abs(desvio) <= ZONA_MORTA:
        # Usa a cor definida pelo Botão C
        np[LED_MEIO] = PALETA[idx_meio]
        estado_led_motor = False 
        
    # 2. Fora da Zona Morta (Em movimento)
    else:
        fator_velocidade = (abs(desvio) - ZONA_MORTA) / (32768 - ZONA_MORTA)
        leds_por_segundo = fator_velocidade * MAX_LEDS_POR_SEGUNDO
        
        if leds_por_segundo < 0.1:
            leds_por_segundo = 0.1

        intervalo_ms = int(1000 / (leds_por_segundo * 2))

        tempo_atual = utime.ticks_ms()
        if utime.ticks_diff(tempo_atual, ultimo_tempo_pisca) >= intervalo_ms:
            estado_led_motor = not estado_led_motor
            ultimo_tempo_pisca = tempo_atual

        if desvio < 0:
            if estado_led_motor:
                # Usa a cor definida pelo Botão A
                np[LED_EXT_ESQUERDA] = PALETA[idx_esq] 
        else:
            if estado_led_motor:
                # Usa a cor definida pelo Botão B
                np[LED_EXT_DIREITA] = PALETA[idx_dir]  

    np.write()
    utime.sleep(0.01)