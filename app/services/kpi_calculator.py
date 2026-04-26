from typing import Dict, List, Any, Optional
import math

class KPICalculator:
    """
    Moteur de calcul des indicateurs académiques à partir de données brutes.
    Gère les données manquantes et calcule les taux selon les règles définies.
    """

    @staticmethod
    def calculate_all(data: Dict[str, Any]) -> Dict[str, Any]:
        results = {}
        warnings = []

        # 1. Extraction des données de base
        students = data.get("students", [])
        total_effectif = data.get("total_effectif")
        sessions_planned = data.get("sessions_planned")
        total_recorded_presence = data.get("total_recorded_presence")

        if not students:
            warnings.append("Aucune liste d'étudiants fournie.")
        
        # --- 1. TAUX DE RÉUSSITE ---
        # (étudiants avec note_finale ≥ 10 / total étudiants notés) × 100
        try:
            graded_students = [s for s in students if s.get("final_grade") is not None]
            if len(graded_students) > 0:
                passing_students = [s for s in graded_students if s.get("final_grade", 0) >= 10]
                results["success_rate"] = round((len(passing_students) / len(graded_students)) * 100, 2)
            else:
                results["success_rate"] = None
                warnings.append("success_rate: Aucun étudiant noté trouvé.")
        except Exception as e:
            results["success_rate"] = None
            warnings.append(f"success_rate: Erreur de calcul ({str(e)})")

        # --- 2. TAUX D'ABANDON ---
        # (inscrits sans présence ET sans note / effectif_total) × 100
        try:
            if total_effectif and total_effectif > 0:
                dropouts = [
                    s for s in students 
                    if s.get("presence_count", 0) == 0 and s.get("final_grade") is None
                ]
                results["dropout_rate"] = round((len(dropouts) / total_effectif) * 100, 2)
            else:
                results["dropout_rate"] = None
                warnings.append("dropout_rate: effectif_total manquant ou nul.")
        except Exception as e:
            results["dropout_rate"] = None
            warnings.append(f"dropout_rate: Erreur de calcul ({str(e)})")

        # --- 3. TAUX DE PRÉSENCE ---
        # (total présences / (effectif_total × seances_prevues)) × 100
        try:
            if total_effectif and sessions_planned and total_recorded_presence is not None:
                denominator = total_effectif * sessions_planned
                if denominator > 0:
                    results["attendance_rate"] = round((total_recorded_presence / denominator) * 100, 2)
                else:
                    results["attendance_rate"] = None
                    warnings.append("attendance_rate: Dénominateur nul (effectif * séances).")
            else:
                results["attendance_rate"] = None
                warnings.append("attendance_rate: Données de présence ou séances manquantes.")
        except Exception as e:
            results["attendance_rate"] = None
            warnings.append(f"attendance_rate: Erreur de calcul ({str(e)})")

        # --- 4. TAUX DE PASSAGE À L'EXAMEN ---
        # (étudiants ayant une note_finale non nulle / effectif_total) × 100
        try:
            if total_effectif and total_effectif > 0:
                students_with_grade = [s for s in students if s.get("final_grade") is not None]
                results["exam_pass_rate"] = round((len(students_with_grade) / total_effectif) * 100, 2)
            else:
                results["exam_pass_rate"] = None
                warnings.append("exam_pass_rate: effectif_total manquant ou nul.")
        except Exception as e:
            results["exam_pass_rate"] = None
            warnings.append(f"exam_pass_rate: Erreur de calcul ({str(e)})")

        # --- 5. TAUX DE REDOUBLEMENT ---
        # (étudiants inscrits comme redoublants / effectif_total) × 100
        try:
            if total_effectif and total_effectif > 0:
                repeaters = [s for s in students if s.get("is_repeating") is True]
                results["grade_repetition_rate"] = round((len(repeaters) / total_effectif) * 100, 2)
            else:
                results["grade_repetition_rate"] = None
                warnings.append("grade_repetition_rate: effectif_total manquant ou nul.")
        except Exception as e:
            results["grade_repetition_rate"] = None
            warnings.append(f"grade_repetition_rate: Erreur de calcul ({str(e)})")

        return {
            "indicators": results,
            "warnings": warnings,
            "metadata": {
                "total_processed": len(students),
                "timestamp": data.get("scan_timestamp")
            }
        }
