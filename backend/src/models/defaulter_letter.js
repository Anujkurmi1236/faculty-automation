import mongoose from 'mongoose';

const defaulterLetterSchema = new mongoose.Schema({
  studentId: { type: mongoose.Schema.Types.ObjectId, ref: 'Student', required: true },
  letterNumber: { type: String, required: true },
  date: { type: Date, default: Date.now },
  subject: { type: String },
  from: { type: String },
  to: { type: String },
  parentName: { type: String },
  attendanceData: {
    theory: { T1: Number, T2: Number, T3: Number, T4: Number },
    practical: { P1: Number, P2: Number }
  },
  generatedAt: { type: Date, default: Date.now }
});

export default mongoose.model('DefaulterLetter', defaulterLetterSchema);