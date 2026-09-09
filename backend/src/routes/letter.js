import express from 'express';
import {
  generateLetter,
  getLetters,
  getLetterById
} from '../controllers/letter_controller.js';

const router = express.Router();

router.post('/generate/:rollNo', generateLetter);
router.get('/', getLetters);
router.get('/:id', getLetterById);

export default router;