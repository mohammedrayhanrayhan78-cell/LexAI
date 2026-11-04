FROM nginx:alpine

COPY index.html /usr/share/nginx/html/index.html
COPY login.html /usr/share/nginx/html/login.html
COPY register.html /usr/share/nginx/html/register.html
COPY chat.html /usr/share/nginx/html/chat.html
COPY css/ /usr/share/nginx/html/css/
COPY js/ /usr/share/nginx/html/js/
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80