import { reactive } from 'vue';

export const loaderState = reactive({
  show: false as boolean,
  text: '' as string,
});

export function showLoader(text: string = '') {
  loaderState.text = text;
  loaderState.show = true;
}

export function hideLoader() {
  loaderState.show = false;
  loaderState.text = '';
}
