from psychopy import visual, event, core


def show_instructions(win, instruction_text):
    """
    Shows one instruction screen and waits for SPACE, ENTER, or RETURN.
    ESCAPE quits the experiment.
    """

    text_stim = visual.TextStim(
        win=win,
        text=instruction_text,
        color='black',
        height=0.035,
        wrapWidth=1.25,
        pos=(0, 0.03),
        alignText='center',
        anchorHoriz='center',
        anchorVert='center'
    )

    continue_text = visual.TextStim(
        win=win,
        text="\n\nPress SPACE to continue",
        color='black',
        height=0.025,
        pos=(0, -0.42),
        alignText='center',
        anchorHoriz='center'
    )

    event.clearEvents(eventType='keyboard')

    text_stim.draw()
    continue_text.draw()
    win.flip()

    while True:
        keys = event.waitKeys(
            keyList=['space', 'return', 'enter', 'escape']
        )

        if keys:
            if 'escape' in keys:
                core.quit()

            if 'space' in keys or 'return' in keys or 'enter' in keys:
                break