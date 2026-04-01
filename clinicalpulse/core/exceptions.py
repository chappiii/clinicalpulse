class CohortNotFoundError(Exception):
    def __init__(self, cohort_id: str):
        self.cohort_id = cohort_id
        super().__init__(f"Cohort expired or does not exist: {cohort_id}")


class LabNotFoundError(Exception):
    def __init__(self, lab_name: str):
        self.lab_name = lab_name
        super().__init__(f"No lab named '{lab_name}' in d_labitems.")


class PatientNotFoundError(Exception):
    def __init__(self, subject_id: int):
        self.subject_id = subject_id
        super().__init__(f"No patient with subject_id {subject_id}.")
