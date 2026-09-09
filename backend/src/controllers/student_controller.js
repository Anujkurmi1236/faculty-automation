import Student from "../models/student";

export const createStudent = async (req, res) => {
  try {
    const student = new Student(req.body);
    await student.save();
    res.status(201).json(student);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
};

export const getStudents = async (req, res) => {
  try {
    const students = await Student.find().sort({ rollNo: 1 });
    res.json(students);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

export const getStudentByRollNo = async (req, res) => {
  try {
    const student = await Student.findOne({ rollNo: req.params.rollNo });
    if (!student) {
      return res.status(404).json({ error: 'Student not found' });
    }
    res.json(student);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

export const updateStudent = async (req, res) => {
  try {
    const student = await Student.findOneAndUpdate(
      { rollNo: req.params.rollNo },
      req.body,
      { new: true }
    );
    if (!student) {
      return res.status(404).json({ error: 'Student not found' });
    }
    res.json(student);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
};

export const deleteStudent = async (req, res) => {
  try {
    const student = await Student.findOneAndDelete({ rollNo: req.params.rollNo });
    if (!student) {
      return res.status(404).json({ error: 'Student not found' });
    }
    res.json({ message: 'Student deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};