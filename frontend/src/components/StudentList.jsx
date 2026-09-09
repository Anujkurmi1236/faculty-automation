import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = 'http://localhost:5000/api';

function StudentList({ onSelectStudent }) {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchStudents();
  }, []);

  const fetchStudents = async () => {
    try {
      const response = await axios.get(`${API_URL}/students`);
      setStudents(response.data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching students:', error);
      setLoading(false);
    }
  };

  const handleDelete = async (rollNo) => {
    if (window.confirm('Are you sure you want to delete this student?')) {
      try {
        await axios.delete(`${API_URL}/students/${rollNo}`);
        fetchStudents();
      } catch (error) {
        alert('Error deleting student: ' + error.response?.data?.error || error.message);
      }
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div className="card">
      <h2>Student List</h2>
      {students.length === 0 ? (
        <p>No students found.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Roll No</th>
              <th>Name</th>
              <th>Class</th>
              <th>Div</th>
              <th>Theory Avg (%)</th>
              <th>Practical Avg (%)</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {students.map((student) => {
              const theoryAvg = Object.values(student.theoryAttendance).reduce((a, b) => a + b, 0) / 4;
              const practicalAvg = Object.values(student.practicalAttendance).reduce((a, b) => a + b, 0) / 2;
              return (
                <tr key={student._id}>
                  <td>{student.rollNo}</td>
                  <td>{student.name}</td>
                  <td>{student.class}</td>
                  <td>{student.division}</td>
                  <td>{theoryAvg.toFixed(1)}</td>
                  <td>{practicalAvg.toFixed(1)}</td>
                  <td>
                    <button onClick={() => onSelectStudent(student)} style={{ marginRight: '8px' }}>
                      Generate Letter
                    </button>
                    <button className="danger" onClick={() => handleDelete(student.rollNo)}>
                      Delete
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default StudentList;