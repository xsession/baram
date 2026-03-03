#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import QObject, Signal

from baramMesh.db.configurations_schema import Step


steps = {
    'geometryStep': Step.GEOMETRY,
    'baseGridStep': Step.BASE_GRID,
    'regionStep': Step.REGION,
    'castellationStep': Step.CASTELLATION,
    'snapStep': Step.SNAP,
    'boundaryLayerStep': Step.BOUNDARY_LAYER,
    'exportStep': Step.EXPORT
}

# Step labels with numbering for visual clarity
_STEP_LABELS = {
    Step.GEOMETRY:       '1. Geometry',
    Step.REGION:         '2. Region',
    Step.BASE_GRID:      '3. Base Grid',
    Step.CASTELLATION:   '4. Castellation',
    Step.SNAP:           '5. Snap',
    Step.BOUNDARY_LAYER: '6. Boundary Layer',
    Step.EXPORT:         '7. Export',
}

# Completed step prefix
_CHECK = '\u2714 '   # ✔
_CURRENT = '\u25b6 ' # ▶


class NavigationView(QObject):
    currentStepChanged = Signal(int, int)

    def __init__(self, ui):
        super().__init__()

        self._ui = ui
        self._steps = ui.stepButtons
        self._currentStep = Step.NONE
        self._workingStep = Step.GEOMETRY
        self._completedSteps = set()

        for b in self._steps.buttons():
            self._steps.setId(b, steps[b.objectName()])

        self._connectSignalsSlots()

    def currentStep(self):
        return self._currentStep

    def setCurrentStep(self, step):
        self._steps.button(step).setChecked(True)
        self._stepChanged(step)

    def enableStep(self, step):
        self._steps.button(step).setEnabled(True)
        # Mark as completed when enabled (it means the step succeeded)
        if step != self._workingStep:
            self._completedSteps.add(step)
        self._updateStepLabels()
        self._updateBatchStepsEnabled()

    def disableStep(self, step):
        if step != Step.SNAP and step != Step.BOUNDARY_LAYER:
            self._steps.button(step).setEnabled(False)
        self._completedSteps.discard(step)
        self._updateStepLabels()
        self._updateBatchStepsEnabled()

    def setWorkingStep(self, step):
        def setBold(button, bold):
            font = button.font()
            font.setBold(bold)
            button.setFont(font)

        self.enableStep(step)
        # Previous working step is now completed
        if self._workingStep != step and self._workingStep != Step.NONE:
            self._completedSteps.add(self._workingStep)
        setBold(self._steps.button(self._workingStep), False)
        self._workingStep = step
        setBold(self._steps.button(step), True)
        self._updateStepLabels()

    def _connectSignalsSlots(self):
        self._steps.idClicked.connect(self._stepChanged)

    def _stepChanged(self, step=None):
        step = self._steps.id(self._steps.checkedButton())
        self.currentStepChanged.emit(step, self._currentStep)
        self._currentStep = step
        self._updateStepLabels()

    def _updateBatchStepsEnabled(self):
        self._ui.snapStep.setEnabled(self._ui.castellationStep.isEnabled())
        self._ui.boundaryLayerStep.setEnabled(self._ui.castellationStep.isEnabled())

    def _updateStepLabels(self):
        """Update step button text with completion checkmarks and current-step indicator."""
        for step, label in _STEP_LABELS.items():
            btn = self._steps.button(step)
            if btn is None:
                continue
            if step in self._completedSteps and step != self._workingStep:
                btn.setText(_CHECK + label)
            elif step == self._currentStep and step == self._workingStep:
                btn.setText(_CURRENT + label)
            else:
                btn.setText(label)
