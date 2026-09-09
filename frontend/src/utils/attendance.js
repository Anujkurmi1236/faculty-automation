export const calculateAttendance = (subject = {}) => {
  const lectures = Number(subject.lectures) || 0;
  const present = Number(subject.present) || 0;
  return lectures > 0 ? (present / lectures) * 100 : 0;
};

export const calculateAverageAttendance = (subjects = {}) => {
  const totals = Object.values(subjects).reduce(
    (result, subject) => ({
      lectures: result.lectures + (Number(subject.lectures) || 0),
      present: result.present + (Number(subject.present) || 0)
    }),
    { lectures: 0, present: 0 }
  );

  return totals.lectures > 0 ? (totals.present / totals.lectures) * 100 : 0;
};

export const formatAttendance = (subject) => `${calculateAttendance(subject).toFixed(1)}%`;
