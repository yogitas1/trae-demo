import React, { useState } from 'react';
import { Calendar, Clock, BookOpen, Plus, Trash2, Target, CheckCircle2 } from 'lucide-react';

const StudyPlanTool = () => {
  const [examName, setExamName] = useState('');
  const [examDate, setExamDate] = useState('');
  const [studyHoursPerDay, setStudyHoursPerDay] = useState(2);
  const [topics, setTopics] = useState([{ name: '', difficulty: 'medium', estimatedHours: 1 }]);
  const [studyPlan, setStudyPlan] = useState(null);
  const [completedTasks, setCompletedTasks] = useState(new Set());

  const addTopic = () => {
    setTopics([...topics, { name: '', difficulty: 'medium', estimatedHours: 1 }]);
  };

  const removeTopic = (index) => {
    setTopics(topics.filter((_, i) => i !== index));
  };

  const updateTopic = (index, field, value) => {
    const updatedTopics = topics.map((topic, i) => 
      i === index ? { ...topic, [field]: value } : topic
    );
    setTopics(updatedTopics);
  };

  const toggleTaskCompletion = (taskId) => {
    const newCompleted = new Set(completedTasks);
    if (newCompleted.has(taskId)) {
      newCompleted.delete(taskId);
    } else {
      newCompleted.add(taskId);
    }
    setCompletedTasks(newCompleted);
  };

  const generateStudyPlan = () => {
    if (!examName || !examDate || topics.length === 0 || topics.some(t => !t.name)) {
      alert('Please fill in all required fields');
      return;
    }

    const today = new Date();
    const examDateTime = new Date(examDate);
    const daysUntilExam = Math.ceil((examDateTime - today) / (1000 * 60 * 60 * 24));
    
    if (daysUntilExam <= 0) {
      alert('Please select a future exam date');
      return;
    }

    const totalEstimatedHours = topics.reduce((sum, topic) => sum + parseInt(topic.estimatedHours), 0);
    const totalAvailableHours = daysUntilExam * studyHoursPerDay;
    
    // Sort topics by difficulty (hard first, then medium, then easy)
    const difficultyOrder = { hard: 3, medium: 2, easy: 1 };
    const sortedTopics = [...topics].sort((a, b) => difficultyOrder[b.difficulty] - difficultyOrder[a.difficulty]);
    
    const plan = [];
    let currentDate = new Date(today);
    let remainingHoursToday = studyHoursPerDay;
    
    for (const topic of sortedTopics) {
      let topicHours = parseInt(topic.estimatedHours);
      
      // Add review sessions (20% of original time)
      const reviewHours = Math.ceil(topicHours * 0.2);
      
      // Initial study
      while (topicHours > 0) {
        const hoursToday = Math.min(remainingHoursToday, topicHours);
        
        if (hoursToday > 0) {
          plan.push({
            id: `${topic.name}-${currentDate.toISOString()}-study`,
            date: new Date(currentDate),
            topic: topic.name,
            type: 'Study',
            hours: hoursToday,
            difficulty: topic.difficulty
          });
          
          topicHours -= hoursToday;
          remainingHoursToday -= hoursToday;
        }
        
        if (remainingHoursToday === 0 || topicHours > 0) {
          currentDate.setDate(currentDate.getDate() + 1);
          remainingHoursToday = studyHoursPerDay;
        }
      }
      
      // Schedule review session 2-3 days before exam
      const reviewDate = new Date(examDateTime);
      reviewDate.setDate(reviewDate.getDate() - Math.min(3, Math.floor(daysUntilExam / 3)));
      
      plan.push({
        id: `${topic.name}-review`,
        date: reviewDate,
        topic: topic.name,
        type: 'Review',
        hours: reviewHours,
        difficulty: topic.difficulty
      });
    }
    
    // Add final review day
    const finalReviewDate = new Date(examDateTime);
    finalReviewDate.setDate(finalReviewDate.getDate() - 1);
    
    plan.push({
      id: 'final-review',
      date: finalReviewDate,
      topic: 'All Topics',
      type: 'Final Review',
      hours: Math.min(studyHoursPerDay, 4),
      difficulty: 'high'
    });
    
    // Sort plan by date
    plan.sort((a, b) => a.date - b.date);
    
    setStudyPlan({
      examName,
      examDate: examDateTime,
      daysUntilExam,
      totalEstimatedHours,
      totalAvailableHours,
      tasks: plan
    });
  };

  const formatDate = (date) => {
    return date.toLocaleDateString('en-US', { 
      weekday: 'short', 
      month: 'short', 
      day: 'numeric' 
    });
  };

  const getDifficultyColor = (difficulty) => {
    switch (difficulty) {
      case 'easy': return 'bg-green-100 text-green-800 border-green-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'hard': return 'bg-red-100 text-red-800 border-red-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getTypeColor = (type) => {
    switch (type) {
      case 'Study': return 'bg-blue-100 text-blue-800';
      case 'Review': return 'bg-purple-100 text-purple-800';
      case 'Final Review': return 'bg-orange-100 text-orange-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 bg-gray-50 min-h-screen">
      <div className="bg-white rounded-lg shadow-lg p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Study Plan Generator</h1>
          <p className="text-gray-600">Create a personalized study schedule for your exams</p>
        </div>

        {!studyPlan ? (
          <div className="space-y-6">
            {/* Exam Details */}
            <div className="bg-blue-50 p-6 rounded-lg">
              <h2 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                <Target className="mr-2 text-blue-600" size={24} />
                Exam Details
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Exam Name *
                  </label>
                  <input
                    type="text"
                    value={examName}
                    onChange={(e) => setExamName(e.target.value)}
                    placeholder="e.g., Biology Final Exam"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Exam Date *
                  </label>
                  <input
                    type="date"
                    value={examDate}
                    onChange={(e) => setExamDate(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Study Hours Per Day
                  </label>
                  <select
                    value={studyHoursPerDay}
                    onChange={(e) => setStudyHoursPerDay(parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {[1, 2, 3, 4, 5, 6, 7, 8].map(hours => (
                      <option key={hours} value={hours}>
                        {hours} hour{hours > 1 ? 's' : ''}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            {/* Topics */}
            <div className="bg-green-50 p-6 rounded-lg">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold text-gray-900 flex items-center">
                  <BookOpen className="mr-2 text-green-600" size={24} />
                  Study Topics
                </h2>
                <button
                  onClick={addTopic}
                  className="flex items-center px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors"
                >
                  <Plus size={16} className="mr-1" />
                  Add Topic
                </button>
              </div>

              <div className="space-y-4">
                {topics.map((topic, index) => (
                  <div key={index} className="flex items-center gap-4 p-4 bg-white rounded-lg border">
                    <div className="flex-1">
                      <input
                        type="text"
                        value={topic.name}
                        onChange={(e) => updateTopic(index, 'name', e.target.value)}
                        placeholder="Topic name *"
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                      />
                    </div>
                    
                    <div className="w-32">
                      <select
                        value={topic.difficulty}
                        onChange={(e) => updateTopic(index, 'difficulty', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                      >
                        <option value="easy">Easy</option>
                        <option value="medium">Medium</option>
                        <option value="hard">Hard</option>
                      </select>
                    </div>
                    
                    <div className="w-32">
                      <input
                        type="number"
                        min="1"
                        max="20"
                        value={topic.estimatedHours}
                        onChange={(e) => updateTopic(index, 'estimatedHours', parseInt(e.target.value))}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                      />
                      <span className="text-xs text-gray-500">hours</span>
                    </div>
                    
                    {topics.length > 1 && (
                      <button
                        onClick={() => removeTopic(index)}
                        className="p-2 text-red-600 hover:bg-red-50 rounded-md transition-colors"
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={generateStudyPlan}
              className="w-full py-3 bg-blue-600 text-white font-semibold rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center"
            >
              <Calendar className="mr-2" size={20} />
              Generate Study Plan
            </button>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Study Plan Header */}
            <div className="bg-blue-50 p-6 rounded-lg">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">{studyPlan.examName}</h2>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
                <div className="bg-white p-4 rounded-lg">
                  <Calendar className="mx-auto mb-2 text-blue-600" size={24} />
                  <div className="text-2xl font-bold text-gray-900">{studyPlan.daysUntilExam}</div>
                  <div className="text-sm text-gray-600">Days Left</div>
                </div>
                
                <div className="bg-white p-4 rounded-lg">
                  <Clock className="mx-auto mb-2 text-green-600" size={24} />
                  <div className="text-2xl font-bold text-gray-900">{studyPlan.totalEstimatedHours}h</div>
                  <div className="text-sm text-gray-600">Total Study Time</div>
                </div>
                
                <div className="bg-white p-4 rounded-lg">
                  <BookOpen className="mx-auto mb-2 text-purple-600" size={24} />
                  <div className="text-2xl font-bold text-gray-900">{topics.length}</div>
                  <div className="text-sm text-gray-600">Topics</div>
                </div>
                
                <div className="bg-white p-4 rounded-lg">
                  <Target className="mx-auto mb-2 text-orange-600" size={24} />
                  <div className="text-2xl font-bold text-gray-900">{studyHoursPerDay}h</div>
                  <div className="text-sm text-gray-600">Daily Hours</div>
                </div>
              </div>
            </div>

            {/* Study Schedule */}
            <div className="bg-white border rounded-lg overflow-hidden">
              <div className="bg-gray-50 px-6 py-3 border-b">
                <h3 className="text-lg font-semibold text-gray-900">Study Schedule</h3>
              </div>
              
              <div className="divide-y">
                {studyPlan.tasks.map((task) => (
                  <div 
                    key={task.id}
                    className={`p-4 flex items-center justify-between hover:bg-gray-50 transition-colors ${
                      completedTasks.has(task.id) ? 'opacity-60 bg-green-50' : ''
                    }`}
                  >
                    <div className="flex items-center space-x-4">
                      <button
                        onClick={() => toggleTaskCompletion(task.id)}
                        className={`w-6 h-6 rounded-full border-2 flex items-center justify-center transition-colors ${
                          completedTasks.has(task.id)
                            ? 'bg-green-600 border-green-600 text-white'
                            : 'border-gray-300 hover:border-green-500'
                        }`}
                      >
                        {completedTasks.has(task.id) && <CheckCircle2 size={16} />}
                      </button>
                      
                      <div>
                        <div className="font-medium text-gray-900">{task.topic}</div>
                        <div className="text-sm text-gray-600">{formatDate(task.date)}</div>
                      </div>
                    </div>
                    
                    <div className="flex items-center space-x-3">
                      <span className={`px-2 py-1 text-xs font-medium rounded-full ${getTypeColor(task.type)}`}>
                        {task.type}
                      </span>
                      
                      {task.difficulty && (
                        <span className={`px-2 py-1 text-xs font-medium rounded border ${getDifficultyColor(task.difficulty)}`}>
                          {task.difficulty}
                        </span>
                      )}
                      
                      <div className="flex items-center text-sm text-gray-600">
                        <Clock size={14} className="mr-1" />
                        {task.hours}h
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex justify-center">
              <button
                onClick={() => setStudyPlan(null)}
                className="px-6 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
              >
                Create New Plan
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default StudyPlanTool;