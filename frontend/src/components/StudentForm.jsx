import React, { useState } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:5000/api';

function StudentForm({ onSuccess }) {
  const [student, setStudent] = useState({
    rollNo: '',
    name: '',
    class: 'BE',
    division: 'A',
    theoryAttendance: { T1: 0, T2: 0, T3: 0, T4: 0 },
    practicalAttendance: { P1: 0, P2: 0 }
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    if (name.startsWith('theory_')) {
      const key = name.split('_')[1];
      setStudent({
        ...student,
        theoryAttendance: { ...student.theoryAttendance, [key]: parseInt(value) || 0 }
      });
    } else if (name.startsWith('practical_')) {
      const key = name.split('_')[1];
      setStudent({
        ...student,
        practicalAttendance: { ...student.practicalAttendance, [key]: parseInt(value) || 0 }
      });
    } else {
      setStudent({ ...student, [name]: value });
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_URL}/students`, student);
      onSuccess();
    } catch (error) {
      alert('Error adding student: ' + error.response?.data?.error || error.message);
    }
  };

  return (
    <div className="card">
      <h2>Add New Student</h2>
      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <div className="form-group">
            <label>Roll No</label>
            <input type="text" name="rollNo" value={student.rollNo} onChange={handleChange} required />
          </div>
          <div className="form-group">
            <label>Name</label>
            <input type="text" name="name" value={student.name} onChange={handleChange} required />
          </div>
          <div className="form-group">
            <label>Class</label>
            <input type="text" name="class" value={student.class} onChange={handleChange} />
          </div>
          <div className="form-group">
            <label>Division</label>
            <input type="text" name="division" value={student.division} onChange={handleChange} />
          </div>
        </div>

        <h3>Theory Attendance (%)</h3>
        <div className="form-row">
          <div className="form-group">
            <label>T1 - DOE</label>
            <input type="number" name="theory_T1" value={student.theoryAttendance.T1} onChange={handleChange} min="0" max="100" />
          </div>
          <div className="form-group">
            <label>T2 - LSCM</label>
            <input type="number" name="theory_T2" value={student.theoryAttendance.T2} onChange={handleChange} min="0" max="100" />
          </div>
          <div className="form-group">
            <label>T3 - PPE</label>
            <input type="number" name="theory_T3" value={student.theoryAttendance.T3} onChange={handleChange} min="0" max="100" />
          </div>
          <div className="form-group">
            <label>T4 - AIML</label>
            <input type="number" name="theory_T4" value={student.theoryAttendance.T4} onChange={handleChange} min="0" max="100" />
          </div>
        </div>

        <h3>Practical Attendance (%)</h3>
        <div className="form-row">
          <div className="form-group">
            <label>P1 - DOE</label>
            <input type="number" name="practical_P1" value={student.practicalAttendance.P1} onChange={handleChange} min="0" max="100" />
          </div>
          <div className="form-group">
            <label>P2 - PPE</label>
            <input type="number" name="practical_P2" value={student.practicalAttendance.P2} onChange={handleChange} min="0" max="100" />
          </div>
        </div>

        <button type="submit">Add Student</button>
      </form>
    </div>
  );
}

export default StudentForm;