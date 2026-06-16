// Получаем все элементы с id="categor" один раз
const elements = document.querySelectorAll('[id="categor"]');

// Функция-обработчик клика
const choice = (e) => {
  // Отменяем стандартное действие, если нужно
  e.preventDefault();
    mark = document.createElement('div')
    mark.id='fixed-block'
    mark.innerText = 'выбран'
  // Проходим по всем элементам
  elements.forEach((element) => {
    div = element.querySelector('#mark');
    if (element !== e.target) {
      div.innerHTML = '';
      element.style.borderColor = 'rgba(123, 122, 122, 0.741)';
    } else {
        div.appendChild(mark)
        element.style.borderColor = 'rgb(0, 0, 225)';
        trafic = document.getElementById('trafic')
        periud = document.getElementById('periud')
        proba = document.getElementById('proba')
         date = document.getElementById('date')
        first = document.getElementById('first')

        periud.innerText ='Месяц'
        data.innerText = `${new Date()}`
    }
  });
};

// Назначаем обработчик клика каждому элементу
elements.forEach((element) => {
  element.addEventListener('click', choice);
});
