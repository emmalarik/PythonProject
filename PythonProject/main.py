import os
import time
import random
import yaml
from PIL import Image
from psychopy import visual, core, event, gui as psychopy_gui

from procedure_io import save_data
from matrix_generator import (
    create_global_machine_pool,
    setup_block_machines,
    get_valid_block_matrix,
)


# =========================================================
# Helper functions
# =========================================================

def find_image(directory, base_name):
    """
    Finds an image by base name, with or without extension.
    Example: find_image('images', 'machine_idle') -> images/machine_idle.png
    """
    if base_name is None:
        raise ValueError("Image name cannot be None")

    base_name = str(base_name).replace('.png', '').replace('.jpg', '').replace('.jpeg', '')

    for ext in ['.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG']:
        path = os.path.join(directory, f"{base_name}{ext}")
        if os.path.exists(path):
            return path

    # Return the expected path anyway, so PsychoPy gives a clear error if the file is missing.
    print(f"!!! BŁĄD: Nie znaleziono pliku: {base_name} w folderze {directory}")
    return os.path.join(directory, f"{base_name}.png")


def ms_to_sec(value_ms):
    return float(value_ms) / 1000.0


def image_size_from_height(image_path, desired_height, fallback_size):
    """
    Returns (width, height) in PsychoPy height units while preserving
    the real image aspect ratio. This prevents machines from looking stretched.
    """
    try:
        with Image.open(image_path) as img:
            width_px, height_px = img.size
        aspect_ratio = width_px / height_px
        return (desired_height * aspect_ratio, desired_height)
    except Exception as err:
        print(f"!!! UWAGA: Nie mogę odczytać proporcji obrazka {image_path}: {err}")
        return tuple(fallback_size)




def collect_required_subject_info():
    """
    Shows the participant form and does not allow the experiment to start
    until ID, age, and gender are provided.
    """
    while True:
        dlg = psychopy_gui.Dlg(title="Multi-armed bandit")
        dlg.addText('Informacje o badanym')
        dlg.addField('Wiek:')
        dlg.addField('ID:')
        dlg.addField('Płeć:', choices=["Kobieta", "Mężczyzna", "Inne"])
        data = dlg.show()

        if not dlg.OK:
            core.quit()

        age = str(data[0]).strip()
        subject_id = str(data[1]).strip()
        gender = str(data[2]).strip()

        errors = []
        if not age:
            errors.append("- Wpisz wiek.")
        elif not age.isdigit() or int(age) <= 0:
            errors.append("- Wiek musi być liczbą większą od 0.")

        if not subject_id:
            errors.append("- Wpisz ID.")

        if not gender:
            errors.append("- Wybierz płeć.")

        if not errors:
            return {
                'Wiek': age,
                'ID': subject_id,
                'Płeć': gender,
            }

        warn = psychopy_gui.Dlg(title="Brakujące dane")
        warn.addText("Proszę uzupełnić wszystkie wymagane pola:\n\n" + "\n".join(errors))
        warn.show()


def show_text_screen(win, text, config):
    """
    Shows an instruction / message screen until continueKey, SPACE, ENTER, or RETURN is pressed.
    Escape quits the experiment.

    No extra English text is added here, because the Polish instruction pages
    already contain "Naciśnij SPACJĘ...".
    """
    continue_key = str(config.get('continueKey', 'space')).lower()
    quit_key = str(config.get('quitKey', 'escape')).lower()

    text_stim = visual.TextStim(
        win=win,
        text=text,
        color=config.get('textColor', 'black'),
        font=config.get('textFont', 'Arial'),
        height=config.get('instructionTextHeight', 0.032),
        wrapWidth=config.get('instructionWrapWidth', 1.25),
        pos=(0, 0.03),
        alignText='center',
        anchorHoriz='center',
        anchorVert='center',
    )

    event.clearEvents(eventType='keyboard')

    text_stim.draw()
    win.flip()

    while True:
        keys = event.waitKeys(
            keyList=[continue_key, 'space', 'return', 'enter', quit_key]
        )

        if not keys:
            continue

        if quit_key in keys:
            win.close()
            core.quit()

        if continue_key in keys or 'space' in keys or 'return' in keys or 'enter' in keys:
            break


def get_instruction_pages(config):
    """
    Uses instructionPages from config.yaml if available.
    If not available, uses the full instruction sequence from the project specification.
    If old instrukcja_powitalna exists, it is shown before the detailed screens.
    """
    if config.get('instructionPages'):
        return config['instructionPages']

    pages = []

    if config.get('instrukcja_powitalna'):
        pages.append(config['instrukcja_powitalna'])

    pages.extend([
        """Witamy! Wyobraź sobie, że odwiedzasz serię wirtualnych kasyn.

W każdym kasynie znajdziesz kilka automatów do gry oznaczonych różnymi symbolami.
Twoim zadaniem będzie zebranie jak największej liczby punktów.

Naciśnij SPACJĘ, aby przejść dalej.""",

        """W każdej próbie na ekranie pojawią się dwa automaty.
Musisz wybrać jeden z nich:

Naciśnij STRZAŁKĘ W LEWO, aby wybrać lewy automat.
Naciśnij STRZAŁKĘ W PRAWO, aby wybrać prawy automat.

Na podjęcie decyzji masz maksymalnie 4 sekundy.
Postaraj się reagować w miarę szybko.""",

        """Automaty różnią się od siebie.

Niektóre częściej dają wygraną, a inne częściej nic nie dają.
Twoim celem jest zorientowanie się, które maszyny w danym kasynie są najbardziej opłacalne i wybieranie ich jak najczęściej.""",

        """Co jakiś czas przejdziesz do nowego kasyna.

Uwaga: w nowym kasynie zasady gry ulegają zmianie!
Nawet jeśli rozpoznasz automat, na którym grałeś/grałaś wcześniej, jego szansa na wygraną mogła ulec zmianie.

W każdym nowym kasynie musisz odkrywać opłacalność maszyn od nowa.""",

        """Zadanie rozpocznie się od krótkiego treningu, aby zapoznać się z klawiszami.

Potem rozpocznie się właściwa gra.

Powodzenia!""",
    ])

    return pages


# =========================================================
# Load config and setup
# =========================================================

with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

subject_data = collect_required_subject_info()

win = visual.Window(
    fullscr=config.get('fullScreen', False),
    size=tuple(config.get('windowSize', [1200, 800])),
    color=config.get('backgroundColor', [205, 205, 205]),
    colorSpace=config.get('colorSpace', 'rgb255'),
    units='height',
)

win.mouseVisible = False

key_left = config.get('leftKey', 'left')
key_right = config.get('rightKey', 'right')
key_quit = config.get('quitKey', 'escape')

img_dir = config.get('imageFolder', 'images')
if not os.path.exists(img_dir):
    print(f"!!! UWAGA: Folder '{img_dir}' nie istnieje w folderze projektu!")

# Machine base images
machine_idle_img = find_image(img_dir, config.get('machineIdleImage', 'machine_idle'))
machine_win_img = find_image(img_dir, config.get('machineWinImage', 'machine_win'))
machine_loss_img = find_image(img_dir, config.get('machineLossImage', 'machine_loss'))

print('Machine image paths:')
print('  idle:', machine_idle_img)
print('  win :', machine_win_img)
print('  loss:', machine_loss_img)

# Layout. You can adjust these numbers if the stimulus is too high/low on the machine.
# By default, machine aspect ratio is preserved from machine_idle.png.
fallback_machine_size = config.get('machineSize', [0.26, 0.38])
if config.get('preserveMachineAspect', True):
    machine_size = image_size_from_height(
        machine_idle_img,
        config.get('machineHeight', fallback_machine_size[1]),
        fallback_machine_size,
    )
else:
    machine_size = tuple(fallback_machine_size)

stimulus_size = tuple(config.get('stimulusSize', [0.095, 0.095]))
left_machine_pos = tuple(config.get('leftMachinePos', [-0.35, 0.0]))
right_machine_pos = tuple(config.get('rightMachinePos', [0.35, 0.0]))
stimulus_x_offset = config.get('stimulusXOffset', 0.0)
stimulus_y_offset = config.get('stimulusYOffset', 0.0)

left_stim_pos = (
    left_machine_pos[0] + stimulus_x_offset,
    left_machine_pos[1] + stimulus_y_offset
)

right_stim_pos = (
    right_machine_pos[0] + stimulus_x_offset,
    right_machine_pos[1] + stimulus_y_offset
)
fixation = visual.TextStim(
    win=win,
    text='+',
    color=config.get('textColor', 'black'),
    font=config.get('textFont', 'Arial'),
    height=config.get('fixationHeight', 0.1),
)

# Two slot machines: base layer
machine_left = visual.ImageStim(
    win=win,
    image=machine_idle_img,
    pos=left_machine_pos,
    size=machine_size,
)

machine_right = visual.ImageStim(
    win=win,
    image=machine_idle_img,
    pos=right_machine_pos,
    size=machine_size,
)

# Stimulus pictures: overlay layer, drawn on the machine body
stimulus_left = visual.ImageStim(
    win=win,
    pos=left_stim_pos,
    size=stimulus_size,
)

stimulus_right = visual.ImageStim(
    win=win,
    pos=right_stim_pos,
    size=stimulus_size,
)


def draw_fixation():
    fixation.draw()
    win.flip()
    core.wait(ms_to_sec(config.get('fixationDuration', 800)))


def draw_decision_screen(left_stim_path, right_stim_path):
    """
    Draws two idle machines and places the stimulus image on each machine.
    """
    machine_left.setImage(machine_idle_img)
    machine_right.setImage(machine_idle_img)

    stimulus_left.setImage(left_stim_path)
    stimulus_right.setImage(right_stim_path)

    machine_left.draw()
    machine_right.draw()
    stimulus_left.draw()
    stimulus_right.draw()
    win.flip()


def draw_feedback_screen(left_stim_path, right_stim_path, choice_made, outcome):
    """
    Feedback screen:
    - selected machine changes from machine_idle to machine_win or machine_loss
    - unselected machine stays machine_idle
    - figures/stimuli stay visible in the same places
    """

    selected_machine_img = machine_win_img if outcome == 1 else machine_loss_img

    if choice_made == key_left:
        machine_left.setImage(selected_machine_img)
        machine_right.setImage(machine_idle_img)

    elif choice_made == key_right:
        machine_left.setImage(machine_idle_img)
        machine_right.setImage(selected_machine_img)

    else:
        machine_left.setImage(machine_idle_img)
        machine_right.setImage(machine_idle_img)

    # Keep the same figures visible during feedback
    stimulus_left.setImage(left_stim_path)
    stimulus_right.setImage(right_stim_path)

    machine_left.draw()
    machine_right.draw()
    stimulus_left.draw()
    stimulus_right.draw()

    win.flip()

def draw_timeout_screen():
    """
    Optional short timeout message.
    By default this is disabled, because the specification says timeout should move to next trial.
    Set showTimeoutMessage: true in config.yaml if you want to show it.
    """
    if not config.get('showTimeoutMessage', False):
        return

    timeout_text = visual.TextStim(
        win=win,
        text=config.get('timeoutMessage', 'Zbyt wolno!'),
        color=config.get('timeoutTextColor', 'red'),
        height=config.get('timeoutTextHeight', 0.07),
    )
    timeout_text.draw()
    win.flip()
    core.wait(ms_to_sec(config.get('timeoutMessageDuration', 500)))


def run_iti():
    """
    Blank screen between trials.
    """
    win.flip()
    iti_ms = random.randint(config.get('itiMin', 800), config.get('itiMax', 1200))
    core.wait(ms_to_sec(iti_ms))


def wait_for_choice():
    """
    Waits for left/right response or timeout.
    Returns: choice_made, rt
    choice_made is key_left, key_right, or 'timeout'.
    rt is seconds or None.
    """
    event.clearEvents(eventType='keyboard')
    timer = core.Clock()

    keys = event.waitKeys(
        maxWait=ms_to_sec(config.get('decisionTimeout', 4000)),
        keyList=[key_left, key_right, key_quit],
        timeStamped=timer,
    )

    if not keys:
        return 'timeout', None

    choice_made, rt = keys[0]

    if choice_made == key_quit:
        win.close()
        core.quit()

    return choice_made, rt


def run_single_trial(
    left_img_path,
    right_img_path,
    left_machine_id,
    right_machine_id,
    left_ev,
    right_ev,
):
    """
    Runs one trial visually and returns choice/outcome information.
    """
    choice_made = 'timeout'
    rt = None
    chosen_id = None
    outcome = 0
    points_delta = 0

    if config.get('showFixationEachTrial', False):
        draw_fixation()

    draw_decision_screen(left_img_path, right_img_path)

    choice_made, rt = wait_for_choice()

    if choice_made != 'timeout':
        chosen_ev = left_ev if choice_made == key_left else right_ev
        chosen_id = left_machine_id if choice_made == key_left else right_machine_id

        if random.random() < chosen_ev:
            outcome = 1
            points_delta = config.get('rewardWinValue', 1)
        else:
            outcome = 0
            points_delta = config.get('rewardLossValue', 0)

        draw_feedback_screen(left_img_path, right_img_path, choice_made, outcome)
        core.wait(ms_to_sec(config.get('feedbackDuration', 1000)))
    else:
        draw_timeout_screen()

    run_iti()

    return {
        'choice_made': choice_made,
        'chosen_machine_id': chosen_id,
        'RT': int(rt * 1000) if rt is not None else None,
        'outcome': outcome,
        'points_delta': points_delta,
    }


# =========================================================
# Instructions
# =========================================================

for page in get_instruction_pages(config):
    show_text_screen(win, page, config)


# =========================================================
# Prepare experiment variables
# =========================================================

experimental_pool, training_pool = create_global_machine_pool()
results_data = []
score_total = 0
global_trial = 0
exp_start_time = time.strftime('%Y%m%d-%H%M%S')


# =========================================================
# Practice phase
# =========================================================

show_text_screen(
    win,
    "Rozpoczynamy fazę treningową.\n\nNaciśnij SPACJĘ, aby rozpocząć.",
    config,
)

practice_left_ev = config.get('practiceLeftEV', 0.8)
practice_right_ev = config.get('practiceRightEV', 0.2)

# Training stimuli come from the 2 machines excluded from the experimental pool.
practice_left_id = training_pool[0]['visual_id']
practice_right_id = training_pool[1]['visual_id']

practice_left_img = find_image(img_dir, practice_left_id)
practice_right_img = find_image(img_dir, practice_right_id)

if config.get('showFixationAtBlockStart', True):
    draw_fixation()

for practice_trial in range(1, config.get('practiceTrials', 5) + 1):
    global_trial += 1

    trial_result = run_single_trial(
        left_img_path=practice_left_img,
        right_img_path=practice_right_img,
        left_machine_id=practice_left_id,
        right_machine_id=practice_right_id,
        left_ev=practice_left_ev,
        right_ev=practice_right_ev,
    )

    # Practice does not add to the final score by default.
    # If you want practice to count, set countPracticeScore: true in config.yaml.
    if config.get('countPracticeScore', False):
        score_total += trial_result['points_delta']

    results_data.append({
        'subject_id': subject_data['ID'],
        'block_number': 0,
        'trial_in_block': practice_trial,
        'block_type': 'practice',
        'global_trial': global_trial,
        'machine_left_id': practice_left_id,
        'machine_right_id': practice_right_id,
        'machine_left_EV': practice_left_ev,
        'machine_right_EV': practice_right_ev,
        'machine_left_novelty': 1,
        'machine_right_novelty': 1,
        'machine_left_exposure_count': practice_trial - 1,
        'machine_right_exposure_count': practice_trial - 1,
        'pair_type': 'standard',
        'choice_made': trial_result['choice_made'],
        'chosen_machine_id': trial_result['chosen_machine_id'],
        'RT': trial_result['RT'],
        'outcome': trial_result['outcome'],
        'score_total': score_total,
    })

    if config.get('saveAfterEachTrial', True):
        save_data(
            results_data,
            subject_data['ID'],
            exp_start_time,
            path=config.get('resultsFolder', 'results'),
        )


# =========================================================
# Experimental phase
# =========================================================

show_text_screen(
    win,
    "Koniec treningu.\n\nPrzechodzimy do właściwego zadania.\n\nNaciśnij SPACJĘ, aby rozpocząć.",
    config,
)

for block_number in range(1, config.get('numberOfBlocks', 20) + 1):
    if block_number > 1:
        show_text_screen(
            win,
            f"Przechodzisz do kasyna nr {block_number}.\n\nNaciśnij SPACJĘ, aby kontynuować.",
            config,
        )

    block_machines = setup_block_machines(
        block_number,
        experimental_pool,
        config.get('expectedValuesArray', [0.2, 0.35, 0.5, 0.65, 0.8]),
    )

    block_matrix = get_valid_block_matrix(
        block_number,
        block_machines,
        experimental_pool,
        config,
    )

    if config.get('showFixationAtBlockStart', True):
        draw_fixation()

    for trial_data in block_matrix:
        global_trial += 1

        left_id = trial_data['machine_left_id']
        right_id = trial_data['machine_right_id']

        left_img_path = find_image(img_dir, left_id)
        right_img_path = find_image(img_dir, right_id)

        trial_result = run_single_trial(
            left_img_path=left_img_path,
            right_img_path=right_img_path,
            left_machine_id=left_id,
            right_machine_id=right_id,
            left_ev=trial_data['machine_left_EV'],
            right_ev=trial_data['machine_right_EV'],
        )

        score_total += trial_result['points_delta']

        results_data.append({
            'subject_id': subject_data['ID'],
            'block_number': block_number,
            'trial_in_block': trial_data['trial_number'],
            'block_type': 'experiment',
            'global_trial': global_trial,
            'machine_left_id': trial_data['machine_left_id'],
            'machine_right_id': trial_data['machine_right_id'],
            'machine_left_EV': trial_data['machine_left_EV'],
            'machine_right_EV': trial_data['machine_right_EV'],
            'machine_left_novelty': trial_data['machine_left_novelty'],
            'machine_right_novelty': trial_data['machine_right_novelty'],
            'machine_left_exposure_count': trial_data['machine_left_exposure_count'],
            'machine_right_exposure_count': trial_data['machine_right_exposure_count'],
            'pair_type': trial_data['pair_type'],
            'choice_made': trial_result['choice_made'],
            'chosen_machine_id': trial_result['chosen_machine_id'],
            'RT': trial_result['RT'],
            'outcome': trial_result['outcome'],
            'score_total': score_total,
        })

        if config.get('saveAfterEachTrial', True):
            save_data(
                results_data,
                subject_data['ID'],
                exp_start_time,
                path=config.get('resultsFolder', 'results'),
            )


# =========================================================
# Save and finish
# =========================================================

save_data(
    results_data,
    subject_data['ID'],
    exp_start_time,
    path=config.get('resultsFolder', 'results'),
)

final_message = config.get('instrukcja_koncowa', 'Dziękujemy za udział w badaniu.')
show_text_screen(
    win,
    f"{final_message}\n\nTwój wynik: {score_total} punktów.\n\nNaciśnij SPACJĘ, aby zakończyć.",
    config,
)

win.close()
core.quit()
