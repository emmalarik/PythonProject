from psychopy import gui, core


def collect_subject_info():
    myDlg = gui.Dlg(title="Multi-armed bandit")
    myDlg.addText('Informacje o badanym')
    myDlg.addField('Wiek:')
    myDlg.addField('ID:')
    myDlg.addField('Płeć:', choices=["Kobieta", "Mężczyzna", "Inne"])
    ok_data = myDlg.show()  # show dialog and wait for OK or Cancel

    if myDlg.OK:  # or if ok_data is not None
        return {
            'Wiek': ok_data[0],
            'ID': ok_data[1],
            'Płeć': ok_data[2]
        }
    else:
        core.quit()