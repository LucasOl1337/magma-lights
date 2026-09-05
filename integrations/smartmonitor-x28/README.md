# SmartMonitor X28 — integração opcional

Código local para a tela USB CDC `1a86:8040`, com comunicação serial exclusiva em 1.000.000 baud, 8N1. Só há comandos de tela; nenhuma rotina altera bomba ou rotação das fans.

- `lcd-control.py off`: envia brilho 1% e timeout de inatividade de um segundo. Foi confirmado pelo usuário como apagamento. **Brilho zero consulta o valor atual**, não apaga.
- `lava/usb.py`: descoberta USB, CRC e pacotes de dados.
- `lava/stats.py`: CPU AMD via k10temp, primeira GPU NVIDIA via `nvidia-smi`, uso de CPU e RAM via `/proc`; envia amostras aproximadamente a cada segundo, com brilho 65% e timeout de cinco segundos.

O mapeamento dos campos do tema é: 1 = CPU °C, 2 = GPU °C, 3 = CPU %, 4 = GPU %, 5 = RAM %. O envio do tema foi aceito pelo dispositivo, mas sua exibição e associação visual dos valores ainda aguardam confirmação.

## Pré-requisitos

A porta serial deve estar acessível ao usuário, `nvidia-smi` precisa funcionar e o dispositivo deve conter um tema compatível com esses campos. Estes scripts não instalam nem transferem esse tema. O tema usado no PC original reutiliza fontes do software do fabricante e não é redistribuído aqui.

Esses requisitos limitam a integração a esse hardware; o VID/PID genérico não garante compatibilidade com qualquer cooler. O script de sensores exige exatamente uma tela correspondente. Não rode o software do fabricante ou outro emissor na mesma serial.

## Instalação manual

Na raiz do repositório:

```bash
mkdir -p ~/.local/share/smartmonitor-x28/lava ~/.local/bin ~/.config/systemd/user
cp integrations/smartmonitor-x28/lcd-control.py ~/.local/share/smartmonitor-x28/
cp integrations/smartmonitor-x28/lava/{usb,stats}.py ~/.local/share/smartmonitor-x28/lava/
cp integrations/smartmonitor-x28/telinha ~/.local/bin/telinha
chmod +x ~/.local/bin/telinha
cp integrations/smartmonitor-x28/smartmonitor-lava.service ~/.config/systemd/user/
systemctl --user daemon-reload
```

A cópia atualiza os arquivos da integração existente. O serviço não é habilitado para iniciar no login.

```bash
~/.local/bin/telinha lava    # Inicia sensores; requer tema já instalado
~/.local/bin/telinha off     # Para sensores antes de enviar apagamento
~/.local/bin/telinha status  # Estado do serviço e última amostra, sem consultar USB
```

`live.json` contém um timestamp; o Magma só exibe dados com menos de oito segundos. Falhas de leitura dos sensores encerram o emissor, em vez de deixá-lo enviando números antigos. O serviço tenta reiniciar com limite de tentativas.

Não continue enviando pacotes depois do apagamento: a comunicação pode manter a tela acesa. Use `telinha off` em vez de chamar `lcd-control.py` enquanto o serviço está ativo. Não é necessário regravar o tema para atualizar sensores ou brilho.
