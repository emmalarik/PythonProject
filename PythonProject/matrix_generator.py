""""
ten plik odpowiada za generowanie puli maszyn, tworzenie
sekwencji prób dla każdego bloku, śledzenie historii ekspozycji
(nowości i niepewności) oraz sprawdzanie wszystkich warunków losowania
"""

import random
import itertools

SHAPES = ['kolo', 'kwadrat', 'szesciokat', 'gwiazda', 'trapez']
TEXTURES = ['paski_pionowe', 'paski_poziome', 'kropki']
COLORS = ['czerwony', 'niebieski', 'zielony']
DEFAULT_EV = [0.2, 0.35, 0.5, 0.65, 0.8]


def create_global_machine_pool():
    """
    generowanie nazw maszyn, żeby móc je rozróżniać
    każda maszyna jest reprezentowana jako słownik przechowujący jej cechy
    """
    pool = []
    machine_id = 1
    for shape in SHAPES:
        for texture in TEXTURES:
            for color in COLORS:
                machine = {
                    'id': machine_id,
                    'visual_id': f"{shape}_{texture}_{color}",
                    'global_exposure_count': 0,
                    'used_in_blocks': []  #czy maszyna była użyta i w którym bloku
                }
                pool.append(machine)
                machine_id += 1

    #mieszam pulę, żeby przypisanie maszyn do bloków nie było alfabetyczne
    random.shuffle(pool)

    # izoluje 2 maszyny dla fazy treningowej
    training_pool = pool[:2]
    experimental_pool = pool[2:]

    return experimental_pool, training_pool

def setup_block_machines(block_number, global_pool, ev_vector=DEFAULT_EV):
    """
    Wybiera 5 maszyn do bieżącego bloku zgodnie z regułami nowości
    i przypisuje im losowo wartości Wartości Oczekiwanej (EV).
    """
    available_ev = ev_vector.copy() #kopiuje, żeby móc losować bez zwracania
    random.shuffle(available_ev)

    #podział maszyn z globalnej puli na nowe i stare
    unused_machines = []
    used_machines = []

    for machine in global_pool:
        #jak nie było użyte to dostajemy pustą listę
        blocks_list = machine.get('used_in_blocks', [])

        # warunek: czy maszyna brała udział w jakimś bloku?
        if len(blocks_list) == 0:
            # jeśli jest pusta, to znaczy, że nie była wyświetlona i trafia do nieużywanych
            unused_machines.append(machine)
        else:
            used_machines.append(machine)

    block_machines = []

    if block_number == 1:
        # blok 1: 5 maszyn całkowicie nowych
        block_machines = unused_machines[:5]

    else:
        selected_known = random.sample(used_machines, 4)

        initial_known = selected_known[:3]  # indexes 0, 1, 2 -> initial set
        holdout_known = selected_known[3]  # index 4 -> second holdout machine

        holdout_new = unused_machines[0]  # index 3 -> first holdout machine

        # Final order matters because generate_block_sequence_candidate()
        # adds block_machines[3] at holdout1_trigger
        # and block_machines[4] at holdout2_trigger.
        block_machines = initial_known + [holdout_new, holdout_known]

    # przypisanie lokalnych parametrów EV do wybranych 5 maszyn z bloku
    for index, machine in enumerate(block_machines):
        machine['current_block_EV'] = available_ev[index] #dodaje do słownika wartość EV dla każdej z maszyn z obecnego bloku
        machine['block_exposure_count'] = 0  # resetuje licznik wewnątrz bloku (miara niepewności)

        # Rozdzielenie na initial i holdout dla 1. i pozostałych bloków
        if block_number == 1:
            machine['set_type'] = 'initial'
        else:
            if index < 3:
                machine['set_type'] = 'initial'
            else:
                machine['set_type'] = 'holdout'

        # Odnotowujemy w historii maszyny, że bierze udział w tym bloku
        if block_number not in machine['used_in_blocks']:
            machine['used_in_blocks'].append(block_number)

    return block_machines


# funkcja, która będzie generować kolejność trialów dla bloku
def generate_block_sequence_candidate(block_number, block_machines, config):
    # określanie długości bloku na postawie config
    block_length = random.randint(config['trialsPerBlockMin'], config['trialsPerBlockMax'])

    # losuje moment wejścia maszyn z holdout z zakresów
    holdout1_trigger = random.randint(3, 5)
    holdout2_trigger = random.randint(8, min(19, block_length))

    # initial set (2 znane, 1 nowa)
    active_pool = [block_machines[0], block_machines[1], block_machines[2]]

    trials_sequence = []
    previous_pair = set()  # bo w listach kolejność ma znaczenie, a my chcemy się upewnić, że jedna para maszyn nie będzie nigdy po sobie (strony nie mają dla nas znaczenia)

    local_exp = {m['id']: 0 for m in block_machines}
    global_exp = {m['id']: m['global_exposure_count'] for m in block_machines}

    for trial_idx in range(1, block_length + 1):
        # Sprawdzamy wprowadzanie maszyn wstrzymanych (Holdout)
        if trial_idx == holdout1_trigger:
            active_pool.append(block_machines[3])
        if trial_idx == holdout2_trigger:
            active_pool.append(block_machines[4])

        # generuje wszystkie kombinacje z active pool
        all_possible_combinations = list(itertools.combinations(active_pool, 2))

        # Filtr par: zostawiamy tylko te, które nie są identyczne z poprzednią parą (n =! n+1)
        legal_pairs = []
        for pair in all_possible_combinations:
            pair_set = {pair[0]['id'], pair[1]['id']}
            if pair_set != previous_pair:
                legal_pairs.append(pair)

        chosen_pair_list = list(random.choice(legal_pairs))
        random.shuffle(chosen_pair_list)

        m_left = chosen_pair_list[0]
        m_right = chosen_pair_list[1]

        # zapisuje obecny wybór jako historię dla następnego trialu
        previous_pair = {m_left['id'], m_right['id']}

        is_novel_l = (global_exp[m_left['id']] == 0)
        is_novel_r = (global_exp[m_right['id']] == 0)
        u_left = local_exp[m_left['id']]
        u_right = local_exp[m_right['id']]

        pair_type = 'standard'

        # WARUNEK A: równa niepewność (obie po 0 w bloku) + różna nowość (jedna nowa globalnie, druga znana)
        if u_left == 0 and u_right == 0:
            if (is_novel_l and not is_novel_r) or (is_novel_r and not is_novel_l):
                pair_type = 'critical_A'

        # WARUNEK B: równa nowość (obie znane globalnie) + różna niepewność (różne liczniki w bloku)
        elif not is_novel_l and not is_novel_r:
            if u_left != u_right:
                pair_type = 'critical_B'

        # zapis próby
        trial_data = {
            'trial_number': trial_idx,
            'machine_left_id': m_left['visual_id'],
            'machine_right_id': m_right['visual_id'],
            'machine_left_EV': m_left['current_block_EV'],
            'machine_right_EV': m_right['current_block_EV'],
            'machine_left_novelty': 1 if is_novel_l else 0,
            'machine_right_novelty': 1 if is_novel_r else 0,
            'machine_left_exposure_count': u_left,
            'machine_right_exposure_count': u_right,
            'pair_type': pair_type,
            '_ref_left': m_left,
            '_ref_right': m_right
        }
        trials_sequence.append(trial_data)

        local_exp[m_left['id']] += 1
        local_exp[m_right['id']] += 1
        global_exp[m_left['id']] += 1
        global_exp[m_right['id']] += 1

    return trials_sequence


# sprawdzamy warunki, wykonuje symulację bloku próba po próbie i sprawdza, czy występują pary krytyczne
def validate_block_sequence(sequence, block_number):
    # w bloku 1. warunki nie mają zastosowania, bo wszystko jest nowe
    if block_number == 1:
        return True

    has_critical_a = any(trial['pair_type'] == 'critical_A' for trial in sequence)
    has_critical_b = any(trial['pair_type'] == 'critical_B' for trial in sequence)

    return has_critical_a and has_critical_b


# generuje ostateczną macierz
def get_valid_block_matrix(block_number, block_machines, global_pool, config):
    valid_matrix = None
    attempts = 0

    while valid_matrix is None:
        attempts += 1

        # generuje kandydata
        candidate = generate_block_sequence_candidate(block_number, block_machines, config)

        # waliduje kandydata
        if validate_block_sequence(candidate, block_number):
            valid_matrix = candidate

        if attempts > 5000:
            raise RuntimeError(f"Algorytm nie mógł wygenerować poprawnego bloku {block_number} po 5000 prób.")

    for trial in valid_matrix:
        # maszyny przypisane do trial to referencje do obiektów w pamięci
        trial['_ref_left']['global_exposure_count'] += 1
        trial['_ref_right']['global_exposure_count'] += 1

    return valid_matrix