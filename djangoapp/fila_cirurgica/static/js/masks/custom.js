var PhoneMaskBehavior = function (val) {
  return val.replace(/\D/g, '').length === 11 ? '(00) 9 0000-0000' : '(00) 9 0000-0000';
},
  phoneOptions = {
    onKeyPress: function (val, e, field, options) {
      field.mask(PhoneMaskBehavior.apply({}, arguments), options);
    }
  };

django.jQuery(function () {
  django.jQuery('.mask-telefone').mask(PhoneMaskBehavior, phoneOptions);

  django.jQuery('.mask-cpf').mask('000-000-000-03', { revrse: true });

  django.jQuery('#paciente_form').submit(function () {

    django.jQuery('#paciente_form').find(":input[class*='mask']").unmask();

  })
});
