// Variáveis

const open = document.querySelector("#open");
const btn = document.querySelector("#btn");
const screenOne = document.querySelector(".screenOne");
const screenTwo = document.querySelector(".screenTwo");

const fortune = [
"O sucesso é uma jornada, não um destino.", "Grandes sonhos começam com pequenas ações.", "As oportunidades surgem quando menos esperamos.", "Acredite em si mesmo e tudo será possível.", "O conhecimento é o tesouro da mente.", "Não tenha medo de falhar, isso faz parte do processo de aprendizagem.", "O tempo cura todas as feridas.", "Uma mente positiva atrai coisas positivas.", "Acredite em seus sonhos e siga em frente.", "As dificuldades são oportunidades disfarçadas.", "A vida é uma aventura, aproveite cada momento.", "O amor é a chave para a felicidade.", "Seja a mudança que você deseja ver no mundo.", "Você é capaz de realizar tudo o que deseja.", "A sorte está sempre do lado daqueles que trabalham duro.", "O sucesso é o resultado da perseverança e da dedicação.", "A verdadeira felicidade vem de dentro.", "A gratidão é a chave para uma vida plena.",
"Você é único e especial, celebre sua individualidade.", "O mundo é seu para explorar, vá em frente e conquiste-o."
]

// Eventos
open.addEventListener('click', firstClick);

btn.addEventListener('click', Click);



// Funções

function firstClick () {
  Click();
  pickFortune();
  
}

function Click(){
  // Pego no documento a classe "screenOne" e adiciono/removo "hide";
  screenOne.classList.toggle("hide");
  // Pego no documento a classe "screenTwo" e removo/adiciono "hide";
  screenTwo.classList.toggle("hide");
}

function pickFortune() {
  let allFortunes = fortune.length
  let randomNumber = Math.floor(Math.random() * allFortunes)  
  screenTwo.querySelector("h2").innerText = `${fortune[randomNumber]}`
}
