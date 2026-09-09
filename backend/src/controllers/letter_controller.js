import DefaulterLetter from '../models/defaulter_letter.js';
import Student from '../models/student.js';
import { v4 as uuidv4 } from 'uuid';

const calculateAttendance = ({ lectures = 0, present = 0 } = {}) => (
  lectures > 0 ? (present / lectures) * 100 : 0
);

const calculateAttendanceData = (attendance = {}) => Object.fromEntries(
  Object.entries(attendance).map(([subject, values]) => [subject, calculateAttendance(values)])
);

export const generateLetter = async (req, res) => {
  try {
    const { rollNo } = req.params;
    const student = await Student.findOne({ rollNo });
    
    if (!student) {
      return res.status(404).json({ error: 'Student not found' });
    }

    const letterNumber = `AF55/${new Date().getFullYear()}/${uuidv4().slice(0, 6)}`;
    
    const letter = new DefaulterLetter({
      studentId: student._id,
      letterNumber,
      subject: `Communication (Intimation No.: ${letterNumber}) regarding poor attendance of your ward`,
      from: 'Class Advisor, BE/Mechanical/Div.A',
      to: student.name,
      parentName: 'Parent/Guardian',
      attendanceData: {
        theory: calculateAttendanceData(student.theoryAttendance),
        practical: calculateAttendanceData(student.practicalAttendance)
      }
    });

    await letter.save();
    res.status(201).json(letter);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
};

export const getLetters = async (req, res) => {
  try {
    const letters = await DefaulterLetter.find()
      .populate('studentId')
      .sort({ generatedAt: -1 });
    res.json(letters);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

export const getLetterById = async (req, res) => {
  try {
    const letter = await DefaulterLetter.findById(req.params.id)
      .populate('studentId');
    if (!letter) {
      return res.status(404).json({ error: 'Letter not found' });
    }
    res.json(letter);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};
