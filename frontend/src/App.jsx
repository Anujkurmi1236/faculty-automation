import React, { useState } from 'react';
import StudentForm from './components/StudentForm';
import StudentList from './components/StudentList';
import LetterGenerator from './components/LetterGenerator';
import LetterView from './components/LetterView';

function App() {
  const [activeTab, setActiveTab] = useState('students');
  const [selectedStudent, setSelectedStudent] = useState(null);

  return (
    <div className="container">
      <h1>AF-55 Defaulter Letter System</h1>
      <div className="nav">
        <button 
          className={activeTab === 'students' ? 'active' : ''}
          onClick={() => setActiveTab('students')}
          style={{ 
            background: 'none', 
            color: activeTab === 'students' ? '#2c3e50' : '#7f8c8d',
            borderBottom: activeTab === 'students' ? '2px solid #2c3e50' : '2px solid transparent',
            padding: '4px 0'
          }}
        >
          Students
        </button>
        <button 
          className={activeTab === 'add' ? 'active' : ''}
          onClick={() => setActiveTab('add')}
          style={{ 
            background: 'none', 
            color: activeTab === 'add' ? '#2c3e50' : '#7f8c8d',
            borderBottom: activeTab === 'add' ? '2px solid #2c3e50' : '2px solid transparent',
            padding: '4px 0'
          }}
        >
          Add Student
        </button>
        <button 
          className={activeTab === 'letter' ? 'active' : ''}
          onClick={() => setActiveTab('letter')}
          style={{ 
            background: 'none', 
            color: activeTab === 'letter' ? '#2c3e50' : '#7f8c8d',
            borderBottom: activeTab === 'letter' ? '2px solid #2c3e50' : '2px solid transparent',
            padding: '4px 0'
          }}
        >
          Generate Letter
        </button>
        <button 
          className={activeTab === 'view' ? 'active' : ''}
          onClick={() => setActiveTab('view')}
          style={{ 
            background: 'none', 
            color: activeTab === 'view' ? '#2c3e50' : '#7f8c8d',
            borderBottom: activeTab === 'view' ? '2px solid #2c3e50' : '2px solid transparent',
            padding: '4px 0'
          }}
        >
          View Letters
        </button>
      </div>

      {activeTab === 'students' && (
        <StudentList onSelectStudent={(student) => {
          setSelectedStudent(student);
          setActiveTab('letter');
        }} />
      )}

      {activeTab === 'add' && (
        <StudentForm onSuccess={() => setActiveTab('students')} />
      )}

      {activeTab === 'letter' && (
        <LetterGenerator 
          selectedStudent={selectedStudent}
          onGenerate={(letter) => {
            setActiveTab('view');
          }}
        />
      )}

      {activeTab === 'view' && <LetterView />}
    </div>
  );
}

export default App;