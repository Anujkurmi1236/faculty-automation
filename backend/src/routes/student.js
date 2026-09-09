import express from 'express';
import {
  createStudent,
  getStudents,
  getStudentByRollNo,
  updateStudent,
  deleteStudent
} from '../controllers/student_controller.js';

const router = express.Router();

router.post('/', createStudent);
router.get('/', getStudents);
router.get('/:rollNo', getStudentByRollNo);
router.put('/:rollNo', updateStudent);
router.delete('/:rollNo', deleteStudent);

export default router;