const KEY = 'sunday_learner'

export function getLearner() {
  try {
    return JSON.parse(localStorage.getItem(KEY) || 'null')
  } catch {
    return null
  }
}

export function saveLearner(learner) {
  localStorage.setItem(KEY, JSON.stringify(learner))
}

export function clearLearner() {
  localStorage.removeItem(KEY)
}
