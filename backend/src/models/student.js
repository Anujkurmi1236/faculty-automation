import mongoose from 'mongoose';

const studentSchema = new mongoose.Schema({
  rollNo: { type: String, required: true, unique: true },
  name: { type: String, required: true },
  class: { type: String, required: true },
  division: { type: String, required: true },
  theoryAttendance: {
    T1: { type: Number, default: 0 },
    T2: { type: Number, default: 0 },
    T3: { type: Number, default: 0 },
    T4: { type: Number, default: 0 }
  },
  practicalAttendance: {
    P1: { type: Number, default: 0 },
    P2: { type: Number, default: 0 }
  },
  createdAt: { type: Date, default: Date.now }
});

export default mongoose.model('Student', studentSchema);