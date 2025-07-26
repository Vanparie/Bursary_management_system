# # utils.py

# def mock_verify_government_id(student_id, guardian_id):
#     """Mock function to simulate government ID + guardian ID verification."""

#     # Mock student records (ID/birth cert -> student data)
#     fake_students = {
#         "12345678": {
#             "full_name": "John Kipkemboi",
#             "dob": "2005-06-15",
#             "constituency_name": "SAMBURU_WEST",
#             "residence": "Samburu West",
#             "guardian_id": "99887766",
#             "type": "id"
#         },
#         "BC-2023-00123": {
#             "full_name": "Aisha Njeri",
#             "dob": "2008-03-22",
#             "constituency_name": "SAMBURU_WEST",
#             "residence": "Samburu North",
#             "guardian_id": "11223344",
#             "type": "birth_cert"
#         }
#     }

#     # Mock guardian records (ID -> guardian data)
#     fake_guardians = {
#         "99887766": {
#             "full_name": "Paul Kipkemboi",
#             "relationship": "Father"
#         },
#         "11223344": {
#             "full_name": "Fatuma Njeri",
#             "relationship": "Mother"
#         }
#     }

#     student = fake_students.get(student_id)

#     if student and student.get("guardian_id") == guardian_id:
#         guardian = fake_guardians.get(guardian_id)
#         if guardian:
#             return {
#                 "student": student,
#                 "guardian": guardian
#             }

#     return None
