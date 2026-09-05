<p align="center"><img src="icon.svg" width="96" alt="Magma"></p>
<h1 align="center">Magma</h1>
<p align="center">Luzes do PC, do seu jeito. Um app nativo para Omarchy e Linux.</p>

Magma reúne presets de cor, intensidade, controles do gabinete e um botão de dormir numa interface GTK4. Foi criado e testado em um PC Omarchy com OpenRGB e uma tela SmartMonitor X28.

## O que faz

- **Seis presets:** Lava, Brasa, Oceano, Aurora, Floresta e Lua.
- **Sua cor:** hexadecimal e intensidade de 10 a 100%.
- **Grupos separados:** fans, RAM e GPU.
- **Modo dormir:** guarda a configuração anterior e apaga gabinete + telinha.
- **Restaurar luzes:** recupera cor, intensidade e grupos anteriores.
- **Painel do cooler:** iniciar stats, apagar a tela e acompanhar temperaturas de CPU/GPU, quando a integração X28 está instalada.

Os botões de dormir e restaurar ficam acessíveis durante a rolagem. Os comandos são executados fora da thread da interface, com indicação de progresso e erro.

## Instalar

Em Arch/Omarchy, as dependências são `python`, `python-gobject`, `python-cairo`, `gtk4` e `openrgb`. O instalador não instala pacotes, não pede root e não envia comandos para dispositivos.

```bash
git clone https://github.com/LucasOl1337/magma-lights.git
cd magma-lights
python install.py
```

Abra **Magma — Luzes do PC** no menu ou execute:

```bash
~/.local/bin/magma-lights
```

Para conferir a interface sem tocar no hardware:

```bash
python app.py --demo
```

A instalação usa `~/.local/share/magma-lights` e `~/.local/bin/magma-lights`. Rodar novamente atualiza o código e preserva `~/.config/magma-lights/state.json`. Não cria autostart nem altera permissões de dispositivos; o OpenRGB precisa já conseguir acessá-los.

## Compatibilidade atual

O perfil é específico do PC em que o app foi desenvolvido. Ainda não há assistente de descoberta nem configuração genérica de dispositivos.

| Grupo | Perfil usado | Estado |
| --- | --- | --- |
| Fans / placa-mãe | MSI B650M PROJECT ZERO (MS-7E09), JRAINBOW | Cor fixa confirmada pelo usuário com Static, brilho 100 e sem seleção de zona |
| RAM | ENE DRAM + Corsair Vengeance RGB DDR5 | Cor via Direct confirmada |
| GPU | ASUS TUF RTX 4070 Ti SUPER Gaming White OC | Cor via Direct confirmada |
| Cooler LCD | SmartMonitor X28, USB `1a86:8040` | Apagamento confirmado; tema/stats com validação visual pendente |
| Teclado | Logitech G515 LS TKL | Botão experimental, sem confirmação de cor |
| FIFINE / MCHOSE | Microfone e periféricos | Controle RGB ainda não implementado |

O botão **Modo dormir** cobre gabinete e cooler. Não promete apagar os periféricos sem suporte. A restauração da telinha é separada: use **Mostrar stats**.

Antes de usar em outro PC, adapte os nomes e modos em `Controller.rgb_command()` e os tamanhos de zona em `Controller.apply_rgb()`. Não trate os comprimentos 200/240/240 como valores universais nem como controle de cada fan individual.

## Como os comandos funcionam

RAM e GPU recebem a cor antes da MSI. As fans recebem o comando final em **Static**, com brilho 100 e sem `--zone`; a intensidade escolhida é aplicada aos componentes RGB da cor. No apagamento, uma chamada separada configura os comprimentos completos 200/240/240, seguida de Direct preto.

Essa ordem incorpora a experiência no hardware: as fans já voltaram a apagar após outras chamadas do OpenRGB. A causa isolada ainda não foi demonstrada. O app evita inventários RGB na abertura e consultas periódicas; seu estado representa **o último comando enviado**, não uma leitura física das luzes.

O controlador serializa suas próprias chamadas com um lock. Um erro não é registrado como aplicação bem-sucedida; comandos parciais já enviados ao hardware não são revertidos automaticamente. Não execute outro controlador OpenRGB simultaneamente. Fechar a janela mantém as luzes e o painel que já estava ativo.

## Terminal e agentes

Depois da instalação:

```bash
python ~/.local/share/magma-lights/controller.py preset lava
python ~/.local/share/magma-lights/controller.py sleep
python ~/.local/share/magma-lights/controller.py restore
python ~/.local/share/magma-lights/controller.py screen_on
python ~/.local/share/magma-lights/controller.py screen_off
python ~/.local/share/magma-lights/controller.py status
```

`status` é passivo: lê somente a configuração salva e a última amostra local de sensores.

## SmartMonitor X28

A interface chama o comando opcional `~/.local/bin/telinha`. Os scripts desenvolvidos para essa integração e as instruções estão em [integrations/smartmonitor-x28](integrations/smartmonitor-x28/README.md).

O instalador principal não configura o cooler. Sem essa integração, os controles RGB continuam disponíveis; ações da telinha mostram um erro. O repositório não inclui o software Windows do fabricante, firmware nem o tema binário que reaproveita fontes proprietárias.

## Desenvolvimento

Os testes do controlador e instalador não acessam hardware nem exigem GTK:

```bash
python -m unittest discover -v
python -m compileall -q .
```

Cobrem restauração de estado, erros parciais, entradas inválidas, concorrência, ordem da MSI, ações da telinha e instalação em um diretório temporário. A interface foi exercitada em GTK Broadway numa sessão isolada. Testes automatizados não substituem confirmação visual das luzes.

O app usa Python, GTK4 e Cairo já disponíveis no sistema. Não usa Electron nem servidor web no funcionamento normal. A integração opcional do cooler mantém seu próprio serviço enquanto o painel está ligado.

Licença [MIT](LICENSE).
